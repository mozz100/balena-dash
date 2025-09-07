use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

// Command reference: https://learn.adafruit.com/usb-plus-serial-backpack/command-reference

fn cool_write(text: &[u8], port: &mut dyn Write) {
    for c in text {
        if let Err(e) = port.write_all(&[*c]) {
            println!("Failed to set up: {}", e);
            return;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
}

fn main() {
    // Flag to stop the loop on Ctrl+C
    let running = Arc::new(AtomicBool::new(true));
    {
        let running = running.clone();
        ctrlc::set_handler(move || {
            println!("\nCtrl+C pressed, shutting down...");
            running.store(false, Ordering::SeqCst);
        })
        .expect("Error setting Ctrl+C handler");
    }

    let mut port: Box<dyn Write> = if false {
        // The serial port to connect to
        let port_name = "/dev/ttyACM0";
        let baud_rate = 9600;
        let sp = serialport::new(port_name, baud_rate)
            .timeout(Duration::from_secs(1))
            .open()
            .expect("Failed opening serial port");
        Box::new(sp)
    } else {
        // File based
        Box::new(
            OpenOptions::new()
                .write(true)
                .open("/tmp/lcd")
                .expect("boom"),
        )
    };

    do_stuff(&mut port, &running);
}

fn do_stuff(port: &mut dyn Write, running: &AtomicBool) {
    // display on. third param ignored
    if let Err(e) = port.write_all(&[0xFE, 0x42, 0]) {
        println!("Failed to go on: {}", e);
        return;
    }

    // FE is command mode
    // 99 is brightness
    // then the value
    // 0xFE 0x50 0xcc sets the contrast
    // clear screen is 0xfe 0x58
    // go home is 0xfe 0x48
    if let Err(e) = port.write_all(&[0xFE, 0x58, 0xFE, 0x48, 0xFE, 0x58, 0xFE, 0x48]) {
        println!("Failed to set up: {}", e);
        return;
    }

    // set colour of screen
    if let Err(e) = port.write_all(&[0xFE, 0xD0, 255, 0, 255]) {
        println!("Failed to set RGB: {}", e);
        return;
    }

    // set block cursor
    if let Err(e) = port.write_all(&[0xFE, 0x53]) {
        println!("Failed to set cursor: {}", e);
        return;
    }

    if let Err(e) = port.write_all(b"Hello") {
        println!("Failed to say hello: {}", e);
        return;
    }
    // newline doesnae seem to work, use 0x0D, that works
    if let Err(e) = port.write_all(&[0x0D]) {
        println!("Failed to write newline: {}", e);
        return;
    }
    cool_write(b"Tickbeat: up", port);

    std::thread::sleep(Duration::from_millis(1500));

    // Periodically send a char
    let mut char = b"1";
    while running.load(Ordering::SeqCst) {
        if let Err(e) = port.write_all(char) {
            eprintln!("Failed to send '.': {}", e);
        } else {
            char = match char {
                b"1" => b"2",
                b"2" => b"3",
                _ => b"1",
            }
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    //clear
    if let Err(e) = port.write_all(&[0xFE, 0x58, 0xFE, 0x48, 0xFE, 0x58, 0xFE, 0x48]) {
        println!("Failed to final clear: {}", e);
        return;
    }
    // set block cursor off
    if let Err(e) = port.write_all(&[0xFE, 0x54]) {
        println!("Failed to set cursor: {}", e);
        return;
    }

    // display off
    if let Err(e) = port.write_all(&[0xFE, 0x46]) {
        println!("Failed to go on: {}", e);
        return;
    }
}
