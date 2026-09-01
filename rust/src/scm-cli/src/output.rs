use std::collections::BTreeMap;
use std::process::ExitCode;

use scm_client::contracts::SearchEnvelope;
use scm_client::{MultiSearchResults, ProviderOutcome};
use serde::Serialize;
use serde_json::Value;

use crate::CliError;

const PROVIDER_ERROR_EXIT_CODE: u8 = 3;
const TABLE_COLUMNS: [(&str, usize); 7] = [
    ("Supplier", 9),
    ("Manufacturer", 12),
    ("MPN", 16),
    ("Supplier PN", 14),
    ("Description", 28),
    ("Price", 14),
    ("Stock", 9),
];

pub(crate) enum CommandOutput {
    Value {
        value: Value,
        provider_error: bool,
    },
    Search {
        document: SearchResultDocument,
        client_error: bool,
        provider_error: bool,
    },
}

#[derive(Serialize)]
pub(crate) struct SearchResultDocument {
    query: String,
    providers: BTreeMap<String, SearchProviderDocument>,
}

#[derive(Serialize)]
#[serde(tag = "outcome", rename_all = "snake_case")]
enum SearchProviderDocument {
    Response { envelope: SearchEnvelope },
    ProviderError { envelope: SearchEnvelope },
    ClientError { error: String },
}

struct TableRow {
    cells: [String; 7],
    stock: i64,
}

impl CommandOutput {
    pub(crate) fn plain<T: Serialize>(value: T) -> Result<Self, CliError> {
        Ok(Self::Value {
            value: serde_json::to_value(value).map_err(CliError::Serialize)?,
            provider_error: false,
        })
    }

    pub(crate) fn provider<T: Serialize>(outcome: ProviderOutcome<T>) -> Result<Self, CliError> {
        let provider_error = matches!(&outcome, ProviderOutcome::ProviderError(_));
        Ok(Self::Value {
            value: serde_json::to_value(outcome.into_envelope()).map_err(CliError::Serialize)?,
            provider_error,
        })
    }

    pub(crate) fn search(query: String, results: MultiSearchResults) -> Self {
        let mut client_error = false;
        let mut provider_error = false;
        let providers = results
            .into_iter()
            .map(|(supplier, result)| {
                let document = match result {
                    Ok(ProviderOutcome::Response(envelope)) => {
                        SearchProviderDocument::Response { envelope }
                    }
                    Ok(ProviderOutcome::ProviderError(envelope)) => {
                        provider_error = true;
                        SearchProviderDocument::ProviderError { envelope }
                    }
                    Err(error) => {
                        client_error = true;
                        SearchProviderDocument::ClientError {
                            error: error.to_string(),
                        }
                    }
                };
                (supplier, document)
            })
            .collect();
        Self::Search {
            document: SearchResultDocument { query, providers },
            client_error,
            provider_error,
        }
    }

    pub(crate) fn exit_code(&self) -> ExitCode {
        match self {
            Self::Search {
                client_error: true, ..
            } => ExitCode::FAILURE,
            Self::Value {
                provider_error: true,
                ..
            }
            | Self::Search {
                provider_error: true,
                ..
            } => ExitCode::from(PROVIDER_ERROR_EXIT_CODE),
            _ => ExitCode::SUCCESS,
        }
    }
}

pub(crate) fn render(output: &CommandOutput, json: bool) -> Result<(), CliError> {
    if json {
        let rendered = match output {
            CommandOutput::Value { value, .. } => serde_json::to_string_pretty(value),
            CommandOutput::Search { document, .. } => serde_json::to_string_pretty(document),
        };
        println!("{}", rendered.map_err(CliError::Serialize)?);
        return Ok(());
    }
    match output {
        CommandOutput::Value { value, .. } => render_value(value),
        CommandOutput::Search { document, .. } => render_search(document),
    }
    Ok(())
}

fn render_value(value: &Value) {
    if let Some(providers) = value.get("providers").and_then(Value::as_object) {
        let mut names = providers.keys().collect::<Vec<_>>();
        names.sort_unstable();
        println!("providers={}", names.len());
        for name in names {
            let configured = providers[name]["configured"].as_bool().unwrap_or(false);
            let backend = providers[name]["backend"].as_str().unwrap_or("-");
            println!(
                "{}\tconfigured={configured}\tbackend={}",
                normalize(name),
                normalize(backend)
            );
        }
        return;
    }
    let status = value
        .get("status")
        .and_then(Value::as_str)
        .unwrap_or("unknown");
    let supplier = value.get("supplier").and_then(Value::as_str);
    let item_count = value.get("data").and_then(Value::as_array).map(Vec::len);
    print!("status={status}");
    if let Some(supplier) = supplier {
        print!(" supplier={}", normalize(supplier));
    }
    if let Some(item_count) = item_count {
        print!(" items={item_count}");
    }
    println!();
}

fn render_search(document: &SearchResultDocument) {
    let mut rows = Vec::new();
    let mut notes = Vec::new();
    for (requested_supplier, result) in &document.providers {
        match result {
            SearchProviderDocument::Response { envelope } => {
                add_rows(&mut rows, requested_supplier, envelope);
                if envelope.status.to_string() != "ok" {
                    notes.push(format!(
                        "{}: {}",
                        normalize(requested_supplier),
                        envelope.status
                    ));
                }
            }
            SearchProviderDocument::ProviderError { envelope } => notes.push(format!(
                "{}: provider_error: {}",
                normalize(requested_supplier),
                normalize(envelope.error.as_deref().unwrap_or("provider failure"))
            )),
            SearchProviderDocument::ClientError { error } => notes.push(format!(
                "{}: client_error: {}",
                normalize(requested_supplier),
                normalize(error)
            )),
        }
    }
    rows.sort_by(|left, right| {
        right
            .stock
            .cmp(&left.stock)
            .then_with(|| left.cells[..4].iter().cmp(right.cells[..4].iter()))
    });
    if rows.is_empty() {
        println!("No parts found for {}.", normalize(&document.query));
    } else {
        print_table(&rows);
    }
    for note in notes {
        println!("{note}");
    }
}

fn add_rows(rows: &mut Vec<TableRow>, requested_supplier: &str, envelope: &SearchEnvelope) {
    for part in envelope.data.iter().flatten() {
        let supplier = if part.supplier.trim().is_empty() {
            requested_supplier
        } else {
            &part.supplier
        };
        let price = part.price_breaks.first().map_or_else(
            || "-".to_owned(),
            |price| format_price(&price.currency, price.unit_price, price.qty.0),
        );
        rows.push(TableRow {
            cells: [
                normalize(supplier),
                normalize(&part.manufacturer),
                normalize(&part.manufacturer_part_number),
                normalize(&part.supplier_part_number),
                normalize(&part.description),
                price,
                format_stock(part.stock_quantity.0),
            ],
            stock: part.stock_quantity.0,
        });
    }
}

fn format_price(currency: &str, unit_price: f64, quantity: i64) -> String {
    let mut amount = format!("{unit_price:.4}");
    while amount.ends_with('0') {
        amount.pop();
    }
    if amount.ends_with('.') {
        amount.pop();
    }
    format!("{} {amount} @ {quantity}", normalize(currency))
}

fn format_stock(stock: i64) -> String {
    let digits = stock.unsigned_abs().to_string();
    let mut grouped =
        String::with_capacity(digits.len() + digits.len() / 3 + usize::from(stock < 0));
    if stock < 0 {
        grouped.push('-');
    }
    for (index, character) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index).is_multiple_of(3) {
            grouped.push(',');
        }
        grouped.push(character);
    }
    grouped
}

fn print_table(rows: &[TableRow]) {
    print_border();
    print_cells(TABLE_COLUMNS.map(|(heading, _)| heading.to_owned()));
    print_border();
    for row in rows {
        print_cells(row.cells.clone());
    }
    print_border();
}

fn print_border() {
    let sections = TABLE_COLUMNS
        .iter()
        .map(|(_, width)| "-".repeat(width + 2))
        .collect::<Vec<_>>();
    println!("+{}+", sections.join("+"));
}

fn print_cells(cells: [String; 7]) {
    let fitted = cells
        .into_iter()
        .zip(TABLE_COLUMNS)
        .map(|(value, (_, width))| format!(" {:width$} ", fit(&value, width)))
        .collect::<Vec<_>>();
    println!("|{}|", fitted.join("|"));
}

fn normalize(value: &str) -> String {
    let mut output = String::new();
    let mut pending_space = false;
    for character in value.chars() {
        if character.is_ascii_graphic() {
            if pending_space && !output.is_empty() {
                output.push(' ');
            }
            output.push(character);
            pending_space = false;
        } else if character.is_ascii_whitespace() {
            pending_space = true;
        } else {
            if pending_space && !output.is_empty() {
                output.push(' ');
            }
            let escaped = if character.is_ascii() {
                format!("\\x{:02X}", character as u32)
            } else {
                format!("\\u{{{:X}}}", character as u32)
            };
            output.push_str(&escaped);
            pending_space = false;
        }
    }
    output
}

fn fit(value: &str, width: usize) -> String {
    let normalized = normalize(value);
    if normalized.chars().count() <= width {
        return normalized;
    }
    normalized.chars().take(width - 3).collect::<String>() + "..."
}

#[cfg(test)]
mod tests {
    use super::{fit, format_price, format_stock, normalize};

    #[test]
    fn human_fields_are_printable_ascii_and_width_bounded() {
        let normalized = normalize("  A\n\t\u{1b}\u{7}Ω  B  ");
        assert_eq!(normalized, "A \\x1B\\x07\\u{3A9} B");
        assert!(normalized.is_ascii());
        assert_eq!(fit(&normalized, 12), "A \\x1B\\x0...");
    }

    #[test]
    fn prices_and_stock_cover_small_large_and_negative_values() {
        assert_eq!(format_price("USD", 0.0001, 1), "USD 0.0001 @ 1");
        assert_eq!(
            format_price("EUR", 123_456_789.25, 10_000),
            "EUR 123456789.25 @ 10000"
        );
        assert_eq!(format_stock(1_234_567), "1,234,567");
        assert_eq!(format_stock(-12_345), "-12,345");
    }
}
