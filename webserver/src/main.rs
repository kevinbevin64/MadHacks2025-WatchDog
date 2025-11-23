use tiny_http::{Method, Request, Response, Server, Header};
use std::io::{Read, Write};
use std::fs::{self, File};

fn main() {
    let server = Server::http("0.0.0.0:8081").unwrap();
    println!("Server running at http://127.0.0.1:8081");

    for request in server.incoming_requests() {
        println!("{:#?}", request.method());
        println!("{:#?}", request.url());
        println!("{:#?}", request.headers());
        
        handle_request(request);
    }
}

fn handle_request(request: Request) {
    match (request.method(), request.url()) {
        (&Method::Post, "/video") => handle_upload_video(request),
        (&Method::Post, "/json") => handle_upload_json(request),
        (&Method::Get, "/video") => handle_download_video(request),
        (&Method::Get, "/json") => handle_download_json(request),
        _ => respond_with_error(request, "Unsupported method", 400),
    }
}

fn handle_upload_video(mut request: Request) {
    let mut content = Vec::new();
    if request.as_reader().read_to_end(&mut content).is_ok() {
        if let Ok(mut file) = File::create("uploaded_video.mp4") {
            file.write_all(&content).unwrap();
            respond_with_message(request, "Video uploaded successfully");
        } else {
            respond_with_error(request, "Failed to save video", 500);
        }
    }
}

fn handle_upload_json(mut request: Request) {
    let mut content = String::new();
    if request.as_reader().read_to_string(&mut content).is_ok() {
        if let Ok(mut file) = File::create("uploaded_data.json") {
            file.write_all(content.as_bytes()).unwrap();
            respond_with_message(request, "JSON uploaded successfully");
        } else {
            respond_with_error(request, "Failed to save JSON", 500);
        }
    }
}

fn handle_download_video(request: Request) {
    if let Ok(mut file) = File::open("uploaded_video.mp4") {
        let mut content = Vec::new();
        file.read_to_end(&mut content).unwrap();
        let response = Response::from_data(content)
            .with_header(Header::from_bytes(&b"Content-Type"[..], &b"video/mp4"[..]).unwrap());
        request.respond(response).unwrap();
    } 
}

fn handle_download_json(request: Request) {
    if let Ok(mut file) = File::open("uploaded_data.json") {
        let mut content = String::new();
        file.read_to_string(&mut content).unwrap();
        let response = Response::from_string(content)
            .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap());
        request.respond(response).unwrap();
    }
}

fn respond_with_message(request: Request, msg: &str) {
    let response = Response::from_string(msg);
    request.respond(response).unwrap();
}

fn respond_with_error(request: Request, msg: &str, code: u32) {
    let response = Response::from_string(msg).with_status_code(code);
    request.respond(response).unwrap();
}
