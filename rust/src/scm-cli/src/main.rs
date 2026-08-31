#![forbid(unsafe_code)]

use std::env;
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::time::Duration;

use clap::{Parser, Subcommand};
use scm_client::{
    ClientError, ConfigError, LookupOptions, ProviderOutcome, ScmClient, SearchOptions,
};
use serde::Serialize;
use serde_json::Value;
use thiserror::Error;

const MAX_CA_BUNDLE_BYTES: usize = 1024 * 1024;
const PROVIDER_ERROR_EXIT_CODE: u8 = 3;

#[derive(Debug, Parser)]
#[command(
    name = "scm",
    version,
    about = "Typed Supply Chain Monkey API client",
    after_help = "Authenticated commands read the bearer token only from SCM_TOKEN."
)]
struct Cli {
    /// SCM service base URL. May also be set with SCM_URL.
    #[arg(long, env = "SCM_URL")]
    url: String,
    /// Print the complete typed response as JSON.
    #[arg(long, global = true)]
    json: bool,
    /// Whole-request timeout in seconds.
    #[arg(long, default_value_t = 30, global = true)]
    timeout_seconds: u64,
    /// Maximum accepted response body size.
    #[arg(long, default_value_t = scm_client::contracts::DEFAULT_MAX_BYTES, global = true)]
    max_response_bytes: usize,
    /// Maximum simultaneous requests used by concurrent client operations.
    #[arg(long, default_value_t = 4, global = true)]
    concurrency: usize,
    /// Explicit private CA PEM bundle. May also be set with SCM_CA_BUNDLE.
    #[arg(long, env = "SCM_CA_BUNDLE", global = true)]
    ca_bundle: Option<PathBuf>,
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Read the unauthenticated health endpoint.
    Health,
    /// List configured providers and capabilities.
    Providers,
    /// Search one supplier by manufacturer part number.
    Search {
        supplier: String,
        mpn: String,
        #[arg(long)]
        include_raw: bool,
        #[arg(long, default_value_t = 10)]
        max_results: u32,
    },
    /// Read detail for a supplier part number.
    Detail {
        supplier: String,
        part: String,
        #[arg(long)]
        include_raw: bool,
    },
    /// Look up one exact supplier part number.
    Spn {
        supplier: String,
        spn: String,
        #[arg(long)]
        include_raw: bool,
    },
    /// Look up one or more exact supplier part numbers.
    Batch {
        supplier: String,
        #[arg(required = true, num_args = 1..)]
        spns: Vec<String>,
        #[arg(long)]
        include_raw: bool,
    },
}

impl Command {
    const fn requires_authentication(&self) -> bool {
        !matches!(self, Self::Health)
    }
}

#[derive(Debug, Error)]
enum CliError {
    #[error("SCM_TOKEN is required for this command")]
    MissingToken,
    #[error("SCM_TOKEN is not valid Unicode")]
    InvalidTokenEncoding,
    #[error("could not read the configured CA bundle")]
    CaBundle(#[source] std::io::Error),
    #[error("configured CA bundle is not a regular file")]
    CaBundleNotRegular,
    #[error("configured CA bundle exceeds the 1 MiB limit")]
    CaBundleTooLarge,
    #[error(transparent)]
    Config(#[from] ConfigError),
    #[error(transparent)]
    Client(#[from] ClientError),
    #[error("could not serialize the typed SCM response")]
    Serialize(#[source] serde_json::Error),
}

struct CommandOutput {
    value: Value,
    provider_error: bool,
}

#[tokio::main]
async fn main() -> ExitCode {
    match run(Cli::parse()).await {
        Ok(code) => code,
        Err(error) => {
            eprintln!("scm: {error}");
            ExitCode::FAILURE
        }
    }
}

async fn run(cli: Cli) -> Result<ExitCode, CliError> {
    let client = build_client(&cli)?;
    let output = execute(&client, cli.command).await?;
    render(&output.value, cli.json)?;
    Ok(if output.provider_error {
        ExitCode::from(PROVIDER_ERROR_EXIT_CODE)
    } else {
        ExitCode::SUCCESS
    })
}

fn build_client(cli: &Cli) -> Result<ScmClient, CliError> {
    let mut builder = ScmClient::builder(&cli.url)?
        .request_timeout(Duration::from_secs(cli.timeout_seconds))
        .max_response_bytes(cli.max_response_bytes)
        .max_concurrency(cli.concurrency);
    if cli.command.requires_authentication() {
        let token = env::var("SCM_TOKEN").map_err(|error| match error {
            env::VarError::NotPresent => CliError::MissingToken,
            env::VarError::NotUnicode(_) => CliError::InvalidTokenEncoding,
        })?;
        builder = builder.bearer_token(&token)?;
    }
    if let Some(path) = &cli.ca_bundle {
        let pem = read_ca_bundle(path)?;
        builder = builder.add_root_certificates_pem(&pem)?;
    }
    builder.build().map_err(CliError::from)
}

fn read_ca_bundle(path: &Path) -> Result<Vec<u8>, CliError> {
    let file = File::open(path).map_err(CliError::CaBundle)?;
    let metadata = file.metadata().map_err(CliError::CaBundle)?;
    if !metadata.is_file() {
        return Err(CliError::CaBundleNotRegular);
    }
    if metadata.len() > MAX_CA_BUNDLE_BYTES as u64 {
        return Err(CliError::CaBundleTooLarge);
    }
    let mut pem = Vec::with_capacity(metadata.len() as usize);
    file.take(MAX_CA_BUNDLE_BYTES as u64 + 1)
        .read_to_end(&mut pem)
        .map_err(CliError::CaBundle)?;
    if pem.len() > MAX_CA_BUNDLE_BYTES {
        return Err(CliError::CaBundleTooLarge);
    }
    Ok(pem)
}

async fn execute(client: &ScmClient, command: Command) -> Result<CommandOutput, CliError> {
    match command {
        Command::Health => plain_output(client.health().await?),
        Command::Providers => plain_output(client.providers_status().await?),
        Command::Search {
            supplier,
            mpn,
            include_raw,
            max_results,
        } => provider_output(
            client
                .search_with_options(
                    &supplier,
                    &mpn,
                    SearchOptions {
                        include_raw,
                        max_results,
                    },
                )
                .await?,
        ),
        Command::Detail {
            supplier,
            part,
            include_raw,
        } => provider_output(
            client
                .detail_with_options(&supplier, &part, LookupOptions { include_raw })
                .await?,
        ),
        Command::Spn {
            supplier,
            spn,
            include_raw,
        } => provider_output(
            client
                .spn_with_options(&supplier, &spn, LookupOptions { include_raw })
                .await?,
        ),
        Command::Batch {
            supplier,
            spns,
            include_raw,
        } => provider_output(
            client
                .spn_batch_with_options(&supplier, spns, LookupOptions { include_raw })
                .await?,
        ),
    }
}

fn plain_output<T: Serialize>(value: T) -> Result<CommandOutput, CliError> {
    Ok(CommandOutput {
        value: serde_json::to_value(value).map_err(CliError::Serialize)?,
        provider_error: false,
    })
}

fn provider_output<T: Serialize>(outcome: ProviderOutcome<T>) -> Result<CommandOutput, CliError> {
    let provider_error = matches!(&outcome, ProviderOutcome::ProviderError(_));
    Ok(CommandOutput {
        value: serde_json::to_value(outcome.into_envelope()).map_err(CliError::Serialize)?,
        provider_error,
    })
}

fn render(value: &Value, json: bool) -> Result<(), CliError> {
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(value).map_err(CliError::Serialize)?
        );
        return Ok(());
    }
    if let Some(providers) = value.get("providers").and_then(Value::as_object) {
        let mut names = providers.keys().collect::<Vec<_>>();
        names.sort_unstable();
        println!("providers={}", names.len());
        for name in names {
            let configured = providers[name]["configured"].as_bool().unwrap_or(false);
            let backend = providers[name]["backend"].as_str().unwrap_or("-");
            println!("{name}\tconfigured={configured}\tbackend={backend}");
        }
        return Ok(());
    }
    let status = value
        .get("status")
        .and_then(Value::as_str)
        .unwrap_or("unknown");
    let supplier = value.get("supplier").and_then(Value::as_str);
    let item_count = value.get("data").and_then(Value::as_array).map(Vec::len);
    print!("status={status}");
    if let Some(supplier) = supplier {
        print!(" supplier={supplier}");
    }
    if let Some(item_count) = item_count {
        print!(" items={item_count}");
    }
    println!();
    Ok(())
}
