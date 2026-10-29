use anyhow::{Context, Result};
use ignore::WalkBuilder;
use rayon::prelude::*;
use regex::Regex;
use serde::Serialize;
use std::{env, fs, path::{Path, PathBuf}, process};

const MAX_FILE_BYTES: u64 = 1_000_000;

#[derive(Serialize)]
struct Finding {
    rule_id: String,
    category: String,
    severity: String,
    confidence: f32,
    file_path: String,
    line: usize,
    title: String,
    evidence: String,
    recommendation: String,
    verification_status: String,
}

struct Rule {
    id: &'static str,
    category: &'static str,
    severity: &'static str,
    confidence: f32,
    pattern: Regex,
    recommendation: &'static str,
}

fn rules() -> Result<Vec<Rule>> {
    let definitions: [(&str, &str, &str, f32, &str, &str); 6] = [
        ("SEC-DYNAMIC-EVAL", "security", "medium", 0.60, r"\b(eval|exec)\s*\(", "Trace whether untrusted input can reach dynamic evaluation."),
        ("SEC-SHELL-TRUE", "security", "medium", 0.65, r"\bshell\s*=\s*True\b", "Review shell argument construction and untrusted-input flow."),
        ("SEC-HARDCODED-SECRET", "security", "high", 0.72, r#"(?i)\b(api[_-]?key|secret|password|access[_-]?token)\b\s*[:=]\s*['"][^'"]{8,}['"]"#, "Rotate exposed credentials if real; move secrets to a managed secret store."),
        ("MAINT-TODO", "maintainability", "info", 0.95, r"\b(TODO|FIXME|XXX)\b", "Confirm whether this marker represents incomplete or risky work."),
        ("RELIABILITY-BARE-EXCEPT", "reliability", "low", 0.65, r"(?m)^\s*except\s*:\s*(?:#.*)?$", "Prefer handling expected exception types explicitly."),
        ("RUST-UNSAFE", "correctness", "low", 0.55, r"\bunsafe\s*\{", "Audit unsafe blocks for valid invariants and memory-safety obligations."),
    ];
    definitions.iter().map(|(id, category, severity, confidence, pattern, recommendation)| {
        Ok(Rule {
            id, category, severity, confidence,
            pattern: Regex::new(pattern).with_context(|| format!("invalid regex for {id}"))?,
            recommendation,
        })
    }).collect()
}

fn supported(path: &Path) -> bool {
    matches!(
        path.extension().and_then(|e| e.to_str()).unwrap_or("").to_ascii_lowercase().as_str(),
        "py" | "pyi" | "js" | "jsx" | "mjs" | "cjs" | "ts" | "tsx" |
        "java" | "go" | "rs" | "rb" | "php" | "sh" | "bash" |
        "yaml" | "yml" | "json" | "toml" | "ini" | "html" | "css"
    )
}

fn inspect_file(root: &Path, path: &Path, rules: &[Rule]) -> Vec<Finding> {
    let Ok(metadata) = fs::metadata(path) else { return Vec::new() };
    if metadata.len() > MAX_FILE_BYTES || !metadata.is_file() { return Vec::new(); }
    let Ok(content) = fs::read_to_string(path) else { return Vec::new() };
    let relative = path.strip_prefix(root).unwrap_or(path).to_string_lossy().replace('\\', "/");
    let mut findings = Vec::new();
    for (line_index, line) in content.lines().enumerate() {
        for rule in rules {
            if !rule.pattern.is_match(line) { continue; }
            let evidence = if rule.id == "SEC-HARDCODED-SECRET" {
                "Potential credential assignment detected; value redacted.".to_string()
            } else {
                line.trim().chars().take(240).collect::<String>()
            };
            findings.push(Finding {
                rule_id: rule.id.to_string(),
                category: rule.category.to_string(),
                severity: rule.severity.to_string(),
                confidence: rule.confidence,
                file_path: relative.clone(),
                line: line_index + 1,
                title: rule.id.replace('-', " ").to_ascii_lowercase(),
                evidence,
                recommendation: rule.recommendation.to_string(),
                verification_status: "unverified".to_string(),
            });
        }
    }
    findings
}

fn main() {
    if let Err(error) = run() {
        eprintln!("review-scan: {error:#}");
        process::exit(2);
    }
}

fn run() -> Result<()> {
    let mut args = env::args().skip(1);
    let root_arg = args.next().context("usage: review-scan <repository-path> [output.json]")?;
    let output = args.next().unwrap_or_else(|| "-".to_string());
    let root = PathBuf::from(root_arg).canonicalize().context("repository path does not exist")?;
    if !root.is_dir() { anyhow::bail!("repository path must be a directory"); }
    let rules = rules()?;
    let paths: Vec<PathBuf> = WalkBuilder::new(&root)
        .hidden(false)
        .git_ignore(true)
        .git_global(true)
        .git_exclude(true)
        .filter_entry(|entry| {
            if entry.depth() == 0 { return true; }
            let name = entry.file_name().to_string_lossy();
            !matches!(name.as_ref(), ".git" | ".venv" | "venv" | "node_modules" | "dist" | "build" | "__pycache__" | ".pytest_cache" | ".mypy_cache" | ".next")
        })
        .build()
        .filter_map(|entry| entry.ok())
        .filter(|entry| entry.file_type().is_some_and(|kind| kind.is_file()))
        .map(|entry| entry.into_path())
        .filter(|path| supported(path))
        .collect();
    let mut findings: Vec<Finding> = paths.par_iter()
        .flat_map_iter(|path| inspect_file(&root, path, &rules))
        .collect();
    findings.sort_by(|a, b| (&a.file_path, a.line, &a.rule_id).cmp(&(&b.file_path, b.line, &b.rule_id)));
    let json = serde_json::to_string_pretty(&findings)?;
    if output == "-" {
        println!("{json}");
    } else {
        fs::write(&output, json).with_context(|| format!("cannot write {output}"))?;
        eprintln!("findings={} report={}", findings.len(), output);
    }
    Ok(())
}
