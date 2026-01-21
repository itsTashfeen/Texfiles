import os
import subprocess
import time


def convert_tex_to_pdf_smart(tex_root, pdf_root):
    aux_extensions_to_delete = [
        '.aux', '.log', '.out', '.toc', '.synctex.gz',
        '.fls', '.fdb_latexmk', '.bbl', '.blg'
    ]

    print(f"Scanning directories...\nFrom: {tex_root}\nTo:   {pdf_root}\n")

    files_processed = 0
    files_skipped = 0

    for dirpath, _, filenames in os.walk(tex_root):
        relative_dir = os.path.relpath(dirpath, tex_root)
        pdf_dir = os.path.join(pdf_root, relative_dir)

        os.makedirs(pdf_dir, exist_ok=True)

        for filename in filenames:
            if filename.endswith(".tex"):
                tex_filepath = os.path.join(dirpath, filename)
                base_name = os.path.splitext(filename)[0]
                pdf_filepath = os.path.join(pdf_dir, base_name + ".pdf")

                if os.path.exists(pdf_filepath):
                    tex_mtime = os.path.getmtime(tex_filepath)
                    pdf_mtime = os.path.getmtime(pdf_filepath)

                    if tex_mtime < pdf_mtime:
                        # The PDF is newer than the source code. No need to compile.
                        # Uncomment the print below if you want to see skipped files
                        print(f"Skipping (Up-to-date): {filename}")
                        files_skipped += 1
                        continue

                print(f"Processing: {filename}")
                files_processed += 1

                try:
                    for i in range(1, 3):
                        print(f"  -> Pass {i}/2...")
                        subprocess.run(
                            ['pdflatex', '-interaction=nonstopmode', '-output-directory', pdf_dir, tex_filepath],
                            check=True,
                            capture_output=True
                        )
                    print(f"  -> Created: {base_name}.pdf")

                except subprocess.CalledProcessError as e:
                    print(f"  -> ERROR: Failed to compile {filename}.")
                    print("=" * 20 + " LaTeX Error Log " + "=" * 20)
                    print(e.stdout.decode(errors='ignore')[-1000:])
                    print("=" * 57)

                except FileNotFoundError:
                    print("CRITICAL ERROR: 'pdflatex' command not found. Install LaTeX.")
                    return

                finally:
                    print("  -> Cleaning temp files...")
                    for ext in aux_extensions_to_delete:
                        aux_file_path = os.path.join(pdf_dir, base_name + ext)
                        if os.path.exists(aux_file_path):
                            try:
                                os.remove(aux_file_path)
                            except OSError:
                                pass

    print("\n" + "=" * 30)
    print(f"Batch Complete.")
    print(f"Files Compiled: {files_processed}")
    print(f"Files Skipped:  {files_skipped}")
    print("=" * 30)


if __name__ == "__main__":
    tex_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\.tex"
    pdf_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\.pdf"

    if not os.path.isdir(tex_directory):
        print(f"Error: Source directory not found at '{tex_directory}'")
    else:
        convert_tex_to_pdf_smart(tex_directory, pdf_directory)