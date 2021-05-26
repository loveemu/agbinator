use std::io;
use std::path::PathBuf;
use byteorder::{LittleEndian, ByteOrder};
use structopt::StructOpt;

/// Scan the ROM of Game Boy Advance to identify the sound driver.
#[derive(StructOpt)]
struct Opt {
    /// ROM files to be scanned
    #[structopt(name = "FILE", parse(from_os_str))]
    files: Vec<PathBuf>
}

fn main() -> io::Result<()> {
    let opt = Opt::from_args();

    for path in opt.files {
        let rom = std::fs::read(path)?;

        let first_instruction = LittleEndian::read_u32(&rom);
        println!("{:#08X}", first_instruction);
    }

    Ok(())
}
