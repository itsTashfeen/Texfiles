import os
import subprocess


def convert_tex_to_pdf_and_cleanup(tex_root, pdf_root):
    """
    Converts all .tex files in a directory and its subdirectories to .pdf files,
    replicating the directory structure in a destination folder and cleaning up
    auxiliary files.

    Args:
        tex_root (str): The path to the root directory containing the .tex files.
        pdf_root (str): The path to the root directory where the .pdf files will be saved.
    """
    # Define the common auxiliary file extensions to be removed
    aux_extensions_to_delete = ['.aux', '.log', '.out', '.toc', '.synctex.gz']

    for dirpath, _, filenames in os.walk(tex_root):
        # Create the corresponding subdirectory in the pdf_root
        relative_dir = os.path.relpath(dirpath, tex_root)
        pdf_dir = os.path.join(pdf_root, relative_dir)

        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir)
            print(f"Created directory: {pdf_dir}")

        for filename in filenames:
            if filename.endswith(".tex"):
                tex_filepath = os.path.join(dirpath, filename)

                # Get the base name of the file (e.g., "Homework 8.1 Arc Length")
                base_name = os.path.splitext(filename)[0]

                print(f"Processing {filename}...")

                # Run the pdflatex command
                try:
                    subprocess.run(
                        ['pdflatex', '-interaction=nonstopmode', '-output-directory', pdf_dir, tex_filepath],
                        check=True,
                        capture_output=True,  # This hides the lengthy pdflatex output unless there's an error
                        text=True
                    )
                    print(f"  -> Successfully converted to {base_name}.pdf")

                    # --- New Cleanup Section ---
                    # After successful conversion, remove the auxiliary files from the pdf_dir
                    for ext in aux_extensions_to_delete:
                        aux_file_path = os.path.join(pdf_dir, base_name + ext)
                        if os.path.exists(aux_file_path):
                            os.remove(aux_file_path)
                    print("  -> Cleaned up auxiliary files.")

                except subprocess.CalledProcessError as e:
                    # If conversion fails, print the LaTeX error log for debugging
                    print(f"  -> Error converting {filename}:")
                    print(e.stdout)  # The stdout from pdflatex contains the detailed error log
                except FileNotFoundError:
                    print("Error: 'pdflatex' command not found.")
                    print(
                        "Please ensure you have a LaTeX distribution (like MiKTeX or TeX Live) installed and in your system's PATH.")
                    return


if __name__ == "__main__":
    # Define your source .tex and destination .pdf directories
    tex_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\Courses\.tex"
    pdf_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\Courses\.pdf"

    convert_tex_to_pdf_and_cleanup(tex_directory, pdf_directory)
    print("\nBatch conversion process finished.")