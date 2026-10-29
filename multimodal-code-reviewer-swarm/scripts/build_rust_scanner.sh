#!/usr/bin/env sh
set -eu
cargo build --release --manifest-path "$(dirname "$0")/../rust-scanner/Cargo.toml"
printf '%s\n' "Build complete. Binary: multimodal-code-reviewer-swarm/rust-scanner/target/release/review-scan"
