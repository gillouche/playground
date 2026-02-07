//! {{SERVICE_NAME}} - Main Application Entry Point
//!
//! A simple HTTP service built with Rust.

use std::env;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};

fn main() {
    let port = env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    let addr = format!("0.0.0.0:{}", port);

    let listener = TcpListener::bind(&addr).expect("Failed to bind to address");
    println!("Starting {{SERVICE_NAME}} on {}", addr);

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                handle_connection(stream);
            }
            Err(e) => {
                eprintln!("Error accepting connection: {}", e);
            }
        }
    }
}

fn handle_connection(mut stream: TcpStream) {
    let mut buffer = [0; 1024];
    if stream.read(&mut buffer).is_err() {
        return;
    }

    let request = String::from_utf8_lossy(&buffer);
    let response = if request.starts_with("GET /healthz") {
        create_response(200, r#"{"status":"healthy"}"#)
    } else if request.starts_with("GET /ready") {
        create_response(200, r#"{"status":"ready"}"#)
    } else if request.starts_with("GET /") {
        create_response(200, r#"{"service":"{{SERVICE_NAME}}","status":"running"}"#)
    } else {
        create_response(404, r#"{"error":"not found"}"#)
    };

    let _ = stream.write_all(response.as_bytes());
}

fn create_response(status: u16, body: &str) -> String {
    let status_text = match status {
        200 => "OK",
        404 => "Not Found",
        _ => "Unknown",
    };

    format!(
        "HTTP/1.1 {} {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{}",
        status,
        status_text,
        body.len(),
        body
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_response() {
        let response = create_response(200, r#"{"test":"value"}"#);
        assert!(response.contains("HTTP/1.1 200 OK"));
        assert!(response.contains("application/json"));
    }
}
