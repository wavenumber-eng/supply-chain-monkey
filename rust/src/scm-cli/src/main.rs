#![forbid(unsafe_code)]

mod output;

use std::collections::BTreeMap;
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
use thiserror::Error;

use output::{CommandOutput, render};

const MAX_CA_BUNDLE_BYTES: usize = 1024 * 1024;

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
    /// Search configured suppliers by manufacturer part number.
    Search {
        mpn: String,
        /// Restrict search to one supplier. Repeat to select several suppliers.
        #[arg(long = "supplier")]
        suppliers: Vec<String>,
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
    #[error("SCM reports no configured search providers")]
    NoConfiguredProviders,
    #[error(transparent)]
    Config(#[from] ConfigError),
    #[error(transparent)]
    Client(#[from] ClientError),
    #[error("could not serialize the typed SCM response")]
    Serialize(#[source] serde_json::Error),
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
    render(&output, cli.json)?;
    Ok(output.exit_code())
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
            mpn,
            suppliers,
            include_raw,
            max_results,
        } => {
            let suppliers = resolve_search_suppliers(client, suppliers).await?;
            let results = client
                .search_all_with_options(
                    &mpn,
                    suppliers,
                    SearchOptions {
                        include_raw,
                        max_results,
                    },
                )
                .await;
            Ok(CommandOutput::search(mpn, results))
        }
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
    CommandOutput::plain(value)
}

fn provider_output<T: Serialize>(outcome: ProviderOutcome<T>) -> Result<CommandOutput, CliError> {
    CommandOutput::provider(outcome)
}

async fn resolve_search_suppliers(
    client: &ScmClient,
    requested: Vec<String>,
) -> Result<Vec<String>, CliError> {
    let normalized = normalize_suppliers(requested);
    if !normalized.is_empty() {
        return Ok(normalized);
    }
    let status = client.providers_status().await?;
    let configured = status
        .providers
        .iter()
        .filter(|(_, provider)| provider.configured)
        .map(|(supplier, _)| supplier.to_ascii_lowercase())
        .collect::<Vec<_>>();
    let configured = normalize_suppliers(configured);
    if configured.is_empty() {
        return Err(CliError::NoConfiguredProviders);
    }
    Ok(configured)
}

fn normalize_suppliers(suppliers: Vec<String>) -> Vec<String> {
    suppliers
        .into_iter()
        .filter_map(|supplier| {
            let supplier = supplier.trim().to_ascii_lowercase();
            (!supplier.is_empty()).then_some((supplier.clone(), supplier))
        })
        .collect::<BTreeMap<_, _>>()
        .into_values()
        .collect()
}
