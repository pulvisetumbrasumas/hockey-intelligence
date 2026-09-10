use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::LazyLock;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::Manager;

const API_URL: &str = "http://127.0.0.1:8000";
const API_ADDR: &str = "127.0.0.1:8000";
const BOOT_TIMEOUT: Duration = Duration::from_secs(45);

static SERVER: LazyLock<Mutex<Option<Child>>> = LazyLock::new(|| Mutex::new(None));

fn python_bin() -> String {
    if let Ok(bin) = std::env::var("HI_PYTHON") {
        if !bin.is_empty() {
            return bin;
        }
    }
    #[cfg(target_os = "windows")]
    {
        return "python".to_string();
    }
    #[cfg(not(target_os = "windows"))]
    "python3".to_string()
}

fn project_root() -> PathBuf {
    if let Ok(dir) = std::env::var("HI_PROJECT_DIR") {
        if !dir.is_empty() {
            return PathBuf::from(dir);
        }
    }
    #[cfg(target_os = "windows")]
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            return dir.to_path_buf();
        }
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn start_api() {
    let bin = python_bin();
    let Ok(child) = Command::new(bin)
        .args([
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ])
        .current_dir(project_root())
        .spawn()
    else {
        // No python on PATH (or a server is already running): if something is
        // already answering on the API port we simply connect to it below.
        return;
    };
    *SERVER.lock().expect("server mutex") = Some(child);
}

fn api_ready() -> bool {
    let Ok(addr) = API_ADDR.parse() else {
        return false;
    };
    TcpStream::connect_timeout(&addr, Duration::from_millis(400)).is_ok()
}

fn bootstrap(handle: tauri::AppHandle) {
    start_api();
    let deadline = Instant::now() + BOOT_TIMEOUT;
    while !api_ready() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(400));
    }
    if let Some(win) = handle.get_webview_window("main") {
        let _ = win.eval(&format!("window.location.replace('{API_URL}')"));
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let handle = app.handle().clone();
            std::thread::spawn(move || bootstrap(handle));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(mut child) = SERVER.lock().expect("server mutex").take() {
                    let _ = child.kill();
                }
            }
        });
}