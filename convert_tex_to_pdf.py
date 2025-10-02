import os
import subprocess


def convert_tex_to_pdf_guaranteed_cleanup(tex_root, pdf_root):

    aux_extensions_to_delete = [
        '.aux', '.log', '.out', '.toc', '.synctex.gz',
        '.fls', '.fdb_latexmk', '.bbl', '.blg'
    ]

    for dirpath, _, filenames in os.walk(tex_root):
        relative_dir = os.path.relpath(dirpath, tex_root)
        pdf_dir = os.path.join(pdf_root, relative_dir)
        os.makedirs(pdf_dir, exist_ok=True)

        for filename in filenames:
            if filename.endswith(".tex"):
                tex_filepath = os.path.join(dirpath, filename)
                base_name = os.path.splitext(filename)[0]

                print(f"\nProcessing: {filename}")

                try:
                    for i in range(1, 3):
                        print(f"  -> Running compile pass {i}/2...")
                        subprocess.run(
                            ['pdflatex', '-interaction=nonstopmode', '-output-directory', pdf_dir, tex_filepath],
                            check=True,
                            capture_output=True
                        )
                    print(f"  -> Successfully created: {base_name}.pdf")

                except subprocess.CalledProcessError as e:
                    print(f"  -> ERROR: Failed to compile {filename}. See log below.")
                    print("=" * 20 + " LaTeX Error Log " + "=" * 20)
                    print(e.stdout.decode(errors='ignore'))
                    print("=" * 57)

                except FileNotFoundError:
                    print("CRITICAL ERROR: 'pdflatex' command not found. Please install a LaTeX distribution.")
                    return

                finally:
                    print("  -> Running cleanup...")
                    for ext in aux_extensions_to_delete:
                        aux_file_path = os.path.join(pdf_dir, base_name + ext)
                        if os.path.exists(aux_file_path):
                            try:
                                os.remove(aux_file_path)
                            except OSError as e:
                                print(f"    -> Warning: Could not delete {aux_file_path}. Reason: {e}")
                    print("  -> Cleanup finished.")


if __name__ == "__main__":
    tex_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\Courses\.tex"
    pdf_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\Courses\.pdf"

    if not os.path.isdir(tex_directory):
        print(f"Error: Source directory not found at '{tex_directory}'")
    else:
        convert_tex_to_pdf_guaranteed_cleanup(tex_directory, pdf_directory)
        print("\n\nBatch conversion process complete.")