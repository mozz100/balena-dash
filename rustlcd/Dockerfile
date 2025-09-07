# Use the official Rust image as the build environment
FROM rust:1.89-bookworm as builder

WORKDIR /app

# # Copy manifests and fetch dependencies
# COPY Cargo.toml Cargo.lock ./
# RUN mkdir src && echo "fn main() {}" > src/main.rs
# RUN cargo fetch

RUN apt update && apt-get install -y libudev-dev
# Copy source code and build
COPY . .
RUN cargo build --release

# Use a minimal base image for running
FROM debian:bookworm-slim

WORKDIR /app

# Copy the compiled binary from the builder stage
COPY --from=builder /app/target/release/rustlcd .

# Set the startup command
CMD ["./rustlcd"]