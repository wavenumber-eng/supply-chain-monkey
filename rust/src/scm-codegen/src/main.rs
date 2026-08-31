#![forbid(unsafe_code)]

//! Deterministic Rust projection of SCM-owned TypeSpec JSON Schemas.

use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use schemars::schema::RootSchema;
use serde_json::{Map, Value, json};
use typify::{TypeSpace, TypeSpaceSettings};

fn main() -> Result<()> {
    let check = env::args().skip(1).any(|argument| argument == "--check");
    let repository = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .context("repository root")?
        .to_path_buf();
    let contract_root = repository.join("contracts/scm/v1/generated");
    let output_root = repository.join("rust/src/scm-contracts/src/generated");
    let resource_root = repository.join("rust/src/scm-contracts/schema");
    let schemas = load_schemas(&contract_root.join("schema"))?;
    let roots = load_roots(&contract_root.join("contract_catalog.a0.json"))?;
    let mut outputs = BTreeMap::new();
    let mut bindings = Vec::new();

    for (schema_id, title) in &roots {
        let source = schemas
            .get(schema_id)
            .with_context(|| format!("catalog root has no schema: {schema_id}"))?;
        let module = rust_module_name(title);
        outputs.insert(
            output_root.join(format!("{module}.rs")),
            generate_binding(source.clone(), &schemas, title)?,
        );
        bindings.push((schema_id.clone(), module, title.clone()));
    }
    outputs.insert(
        output_root.join("mod.rs"),
        generate_registry(&bindings, &schemas)?,
    );
    for schema in schemas.values() {
        let title = schema["title"].as_str().context("schema title")?;
        let source =
            fs::read_to_string(contract_root.join("schema").join(format!("{title}.json")))?;
        outputs.insert(resource_root.join(format!("{title}.json")), source);
    }
    enforce_inventory(&output_root, &outputs, check)?;
    enforce_inventory(&resource_root, &outputs, check)?;
    write_or_check(outputs, check)?;
    println!(
        "{} Rust SCM bindings: {} catalog roots",
        if check { "Checked" } else { "Generated" },
        bindings.len()
    );
    Ok(())
}

fn load_schemas(root: &Path) -> Result<BTreeMap<String, Value>> {
    let mut schemas = BTreeMap::new();
    for entry in fs::read_dir(root).with_context(|| format!("read {}", root.display()))? {
        let entry = entry?;
        let path = entry.path();
        let file_type = entry.file_type()?;
        if !file_type.is_file() || file_type.is_symlink() {
            bail!("schema input is not a regular file: {}", path.display());
        }
        if path.extension().and_then(|value| value.to_str()) != Some("json") {
            bail!("unexpected schema input {}", path.display());
        }
        let mut schema: Value = serde_json::from_slice(&fs::read(&path)?)?;
        let title = path
            .file_stem()
            .and_then(|value| value.to_str())
            .context("schema file stem")?;
        schema
            .as_object_mut()
            .context("schema root must be an object")?
            .insert("title".to_owned(), Value::String(title.to_owned()));
        let schema_id = schema
            .get("$id")
            .and_then(Value::as_str)
            .with_context(|| format!("{}: missing schema identity", path.display()))?
            .to_owned();
        if schemas.insert(schema_id.clone(), schema).is_some() {
            bail!("duplicate schema identity {schema_id}");
        }
    }
    if schemas.is_empty() {
        bail!("no generated SCM schemas found");
    }
    Ok(schemas)
}

fn load_roots(path: &Path) -> Result<Vec<(String, String)>> {
    let catalog: Value = serde_json::from_slice(&fs::read(path)?)?;
    let roots = catalog["roots"].as_array().context("catalog roots")?;
    roots
        .iter()
        .map(|root| {
            let schema_id = root["schema_id"].as_str().context("root schema_id")?;
            let qualified = root["name"].as_str().context("root name")?;
            let title = qualified.rsplit('.').next().context("root local name")?;
            Ok((schema_id.to_owned(), title.to_owned()))
        })
        .collect()
}

fn rust_module_name(value: &str) -> String {
    let mut output = String::new();
    for (index, character) in value.chars().enumerate() {
        if character.is_ascii_uppercase() && index > 0 {
            output.push('_');
        }
        output.push(character.to_ascii_lowercase());
    }
    output
}

fn generate_binding(
    mut schema: Value,
    schemas: &BTreeMap<String, Value>,
    title: &str,
) -> Result<String> {
    schema
        .as_object_mut()
        .context("root schema object")?
        .insert("title".to_owned(), Value::String(title.to_owned()));
    bundle_external_references(&mut schema, schemas)?;
    project_for_typify(&mut schema)?;
    let root: RootSchema = serde_json::from_value(schema)?;
    let mut settings = TypeSpaceSettings::default();
    settings.with_struct_builder(false);
    let mut type_space = TypeSpace::new(&settings);
    type_space.add_root_schema(root)?;
    let source = format!(
        "#![allow(dead_code, reason = \"generated roots contain projection helpers\")]\n\n\
         // Generated from SCM TypeSpec JSON Schema.\n\
         // Runtime validation uses the unmodified schema. Do not edit.\n\n{}\n",
        type_space.to_stream()
    );
    let syntax = syn::parse_file(&source).context("parse generated Rust binding")?;
    let formatted = prettyplease::unparse(&syntax);
    let closed = add_closed_struct_attributes(&formatted);
    let syntax = syn::parse_file(&closed).context("parse closed generated Rust binding")?;
    Ok(prettyplease::unparse(&syntax))
}

fn add_closed_struct_attributes(source: &str) -> String {
    let mut output = String::new();
    for line in source.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("pub struct ") && trimmed.ends_with('{') {
            output.push_str("#[serde(deny_unknown_fields)]\n");
        }
        output.push_str(line);
        output.push('\n');
    }
    output
}

fn generate_registry(
    bindings: &[(String, String, String)],
    schemas: &BTreeMap<String, Value>,
) -> Result<String> {
    let mut source = String::from("// Generated SCM v1 root registry. Do not edit.\n\n");
    for (_, module, title) in bindings {
        source.push_str(&format!(
            "#[allow(clippy::derivable_impls, reason = \"typify emits explicit defaults\")]\n\
             #[rustfmt::skip]\n\
             mod {module};\n\
             pub use {module}::{title};\n"
        ));
    }
    source.push_str("\n#[derive(Clone, Copy, Debug, Eq, PartialEq)]\npub enum ContractRoot {\n");
    for (_, _, title) in bindings {
        source.push_str(&format!("    {title},\n"));
    }
    source.push_str("}\n\nimpl ContractRoot {\n");
    source.push_str("    pub const ALL: &'static [Self] = &[\n");
    for (_, _, title) in bindings {
        source.push_str(&format!("        Self::{title},\n"));
    }
    source.push_str(
        "    ];\n\n    pub const fn schema_id(self) -> &'static str {\n        match self {\n",
    );
    for (schema_id, _, title) in bindings {
        source.push_str(&format!("            Self::{title} => {schema_id:?},\n"));
    }
    source.push_str("        }\n    }\n\n    pub const fn schema(self) -> &'static str {\n        match self {\n");
    for (_, _, title) in bindings {
        source.push_str(&format!(
            "            Self::{title} => include_str!(concat!(env!(\"CARGO_MANIFEST_DIR\"), \"/schema/{title}.json\")),\n"
        ));
    }
    source.push_str("        }\n    }\n}\n\n");
    source.push_str("pub(crate) const GENERATED_SCHEMAS: &[(&str, &str)] = &[\n");
    for (schema_id, schema) in schemas {
        let title = schema["title"].as_str().context("schema title")?;
        source.push_str(&format!(
            "    ({schema_id:?}, include_str!(concat!(env!(\"CARGO_MANIFEST_DIR\"), \"/schema/{title}.json\"))),\n"
        ));
    }
    source.push_str("];\n");
    let syntax = syn::parse_file(&source).context("parse generated Rust registry")?;
    Ok(prettyplease::unparse(&syntax))
}

fn bundle_external_references(root: &mut Value, schemas: &BTreeMap<String, Value>) -> Result<()> {
    let mut pending = Vec::new();
    collect_external_references(root, &mut pending);
    let mut references = BTreeMap::new();
    let mut bundled = BTreeMap::new();
    while let Some(schema_id) = pending.pop() {
        if references.contains_key(&schema_id) {
            continue;
        }
        let prefix = external_definition_prefix(&schema_id);
        references.insert(schema_id.clone(), format!("#/$defs/{prefix}"));
        let mut schema = schemas
            .get(&schema_id)
            .with_context(|| format!("unresolved SCM schema {schema_id}"))?
            .clone();
        collect_external_references(&schema, &mut pending);
        let object = schema.as_object_mut().context("external schema root")?;
        object.remove("$schema");
        object.remove("$id");
        object.remove("title");
        rewrite_local_references(&mut schema, &prefix);
        if bundled.insert(prefix.clone(), schema).is_some() {
            bail!("external definition collision {prefix}");
        }
    }
    rewrite_external_references(root, &references)?;
    let definitions = root
        .as_object_mut()
        .context("schema root")?
        .entry("$defs")
        .or_insert_with(|| Value::Object(Map::new()))
        .as_object_mut()
        .context("schema definitions")?;
    for (name, mut definition) in bundled {
        rewrite_external_references(&mut definition, &references)?;
        definitions.insert(name, definition);
    }
    Ok(())
}

fn collect_external_references(value: &Value, output: &mut Vec<String>) {
    match value {
        Value::Array(items) => items
            .iter()
            .for_each(|item| collect_external_references(item, output)),
        Value::Object(object) => {
            if let Some(reference) = object.get("$ref").and_then(Value::as_str)
                && !reference.starts_with('#')
            {
                output.push(reference.to_owned());
            }
            object
                .values()
                .for_each(|item| collect_external_references(item, output));
        }
        _ => {}
    }
}

fn rewrite_local_references(value: &mut Value, prefix: &str) {
    visit_references(value, &mut |reference| {
        reference
            .strip_prefix("#/$defs/")
            .map(|name| format!("#/$defs/{prefix}__{name}"))
    });
}

fn rewrite_external_references(
    value: &mut Value,
    references: &BTreeMap<String, String>,
) -> Result<()> {
    let mut unresolved = None;
    visit_references(value, &mut |reference| {
        if reference.starts_with('#') {
            return None;
        }
        references.get(reference).cloned().or_else(|| {
            unresolved = Some(reference.to_owned());
            None
        })
    });
    if let Some(reference) = unresolved {
        bail!("unresolved external reference {reference}");
    }
    Ok(())
}

fn visit_references(value: &mut Value, visitor: &mut impl FnMut(&str) -> Option<String>) {
    match value {
        Value::Array(items) => items
            .iter_mut()
            .for_each(|item| visit_references(item, visitor)),
        Value::Object(object) => {
            if let Some(reference) = object.get("$ref").and_then(Value::as_str)
                && let Some(replacement) = visitor(reference)
            {
                object.insert("$ref".to_owned(), Value::String(replacement));
            }
            object
                .values_mut()
                .for_each(|item| visit_references(item, visitor));
        }
        _ => {}
    }
}

fn external_definition_prefix(schema_id: &str) -> String {
    format!(
        "External_{}",
        schema_id
            .chars()
            .map(|character| if character.is_ascii_alphanumeric() {
                character
            } else {
                '_'
            })
            .collect::<String>()
    )
}

fn project_for_typify(value: &mut Value) -> Result<()> {
    match value {
        Value::Array(items) => {
            for item in items {
                project_for_typify(item)?;
            }
        }
        Value::Object(object) => {
            project_literal_union(object);
            project_record(object);
            project_flexible_json_number(object);
            if object
                .get("unevaluatedProperties")
                .is_some_and(is_false_schema)
            {
                object.remove("unevaluatedProperties");
            }
            if let Some(constant) = object.remove("const") {
                object.insert("enum".to_owned(), Value::Array(vec![constant]));
            }
            for item in object.values_mut() {
                project_for_typify(item)?;
            }
        }
        _ => {}
    }
    Ok(())
}

fn project_record(object: &mut Map<String, Value>) {
    let is_empty_object = object.get("type").and_then(Value::as_str) == Some("object")
        && object
            .get("properties")
            .and_then(Value::as_object)
            .is_some_and(Map::is_empty);
    if is_empty_object && let Some(values) = object.remove("unevaluatedProperties") {
        object.insert("additionalProperties".to_owned(), values);
    }
}

fn project_flexible_json_number(object: &mut Map<String, Value>) {
    let Some(branches) = object.get_mut("anyOf").and_then(Value::as_array_mut) else {
        return;
    };
    let number_index = branches
        .iter()
        .position(|branch| branch.get("type").and_then(Value::as_str) == Some("number"));
    let recursive = branches.iter().any(|branch| branch.get("items").is_some());
    let integer = branches
        .iter()
        .any(|branch| branch.get("type").and_then(Value::as_str) == Some("integer"));
    if let Some(index) = number_index
        && recursive
        && !integer
    {
        branches.insert(index, json!({"type": "integer"}));
    }
}

fn project_literal_union(object: &mut Map<String, Value>) {
    let Some(values) = object
        .get("anyOf")
        .and_then(Value::as_array)
        .and_then(|branches| {
            branches
                .iter()
                .map(|branch| branch.get("const").cloned())
                .collect::<Option<Vec<_>>>()
        })
    else {
        return;
    };
    object.clear();
    object.insert("enum".to_owned(), Value::Array(values));
}

fn is_false_schema(value: &Value) -> bool {
    value.as_object().is_some_and(|object| {
        object.len() == 1 && object.get("not") == Some(&Value::Object(Map::new()))
    })
}

fn enforce_inventory(
    output_root: &Path,
    outputs: &BTreeMap<PathBuf, String>,
    check: bool,
) -> Result<()> {
    let expected = outputs.keys().collect::<BTreeSet<_>>();
    if !output_root.exists() {
        return Ok(());
    }
    for entry in fs::read_dir(output_root)? {
        let entry = entry?;
        let path = entry.path();
        let file_type = entry.file_type()?;
        if !file_type.is_file() || file_type.is_symlink() {
            bail!(
                "generated artifact is not a regular file: {}",
                path.display()
            );
        }
        if !expected.contains(&path) {
            if check {
                bail!("unexpected generated Rust file {}", path.display());
            }
            fs::remove_file(path)?;
        }
    }
    Ok(())
}

fn write_or_check(outputs: BTreeMap<PathBuf, String>, check: bool) -> Result<()> {
    for (path, expected) in outputs {
        if check {
            let actual = fs::read_to_string(&path)
                .with_context(|| format!("missing generated Rust file {}", path.display()))?;
            if actual != expected {
                bail!("stale generated Rust file {}", path.display());
            }
        } else {
            fs::create_dir_all(path.parent().context("generated output parent")?)?;
            fs::write(path, expected)?;
        }
    }
    Ok(())
}
