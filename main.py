import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import timeimport subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import re
import os # Needed for path manipulation
import shutil # Needed for portable file copying

class VideoEditorApp:
    # Keep the __init__, check_ffmpeg_installed, show_ffmpeg_warning,
    # create_widgets, seleccionar_video, seleccionar_salida,
    # iniciar_proceso, cancelar_proceso, on_close methods AS IS.
    # Only the `procesar_video` method needs significant changes.

    def __init__(self, root):
        self.root = root
        self.root.title("Editor de Video Silencioso")
        self.root.geometry("800x600")
        self.root.configure(bg="#1e1e1e")

        # Estilos personalizados
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TLabel", foreground="#d0d0d0", background="#1e1e1e", font=("Segoe UI", 10))
        self.style.configure("TButton", foreground="#ffffff", background="#4CAF50",
                             font=("Segoe UI", 10), borderwidth=0, relief="flat") # Use flat for modern look
        self.style.map("TButton",
                       foreground=[('active', '#ffffff')],
                       background=[('active', '#388E3C')],
                       relief=[('pressed', 'sunken'), ('!pressed', 'flat')]) # Adjust relief
        self.style.configure("TEntry", foreground="#d0d0d0", background="#2a2a2a", # Lighter foreground for entry
                             font=("Segoe UI", 10), fieldbackground="#2a2a2a",
                             insertbackground="#d0d0d0", # Make cursor visible
                             borderwidth=1, relief="solid") # Add subtle border
        self.style.configure("TProgressbar", background="#4CAF50", troughcolor="#2a2a2a",
                             bordercolor="#2a2a2a", thickness=15) # Make progress bar thicker
        self.style.configure("TCombobox", foreground="#d0d0d0", background="#2a2a2a",
                             fieldbackground="#2a2a2a", selectbackground="#4CAF50",
                             selectforeground="#ffffff", arrowcolor="#d0d0d0",
                             font=("Segoe UI", 10), borderwidth=1, relief="solid")
        self.style.map('TCombobox', fieldbackground=[('readonly', '#2a2a2a')])
        self.style.map('TCombobox', selectbackground=[('readonly', '#4CAF50')])
        self.style.map('TCombobox', selectforeground=[('readonly', '#ffffff')])


        # Variables
        self.video_path = tk.StringVar()
        self.output_path = tk.StringVar()
        # Use dB for threshold, consistent with ffmpeg silencedetect noise=-XXdB format
        self.silence_threshold = tk.StringVar(value="-30") # Default to -30dB, more common starting point
        self.min_silence_duration = tk.DoubleVar(value=0.5) # Default 0.5s
        self.audio_bitrate = tk.StringVar(value="192k") # Default 192k is a good balance
        self.process_running = tk.BooleanVar(value=False)
        self.ffmpeg_process = None # To store the running subprocess instance
        self.thread = None

        # Check FFmpeg FIRST
        self.ffmpeg_installed = self.check_ffmpeg_installed()
        self.ffprobe_installed = self.check_ffprobe_installed()

        # Interfaz de usuario
        self.create_widgets()

        if not self.ffmpeg_installed or not self.ffprobe_installed:
            self.show_ffmpeg_warning(not self.ffmpeg_installed, not self.ffprobe_installed)

    def check_ffmpeg_installed(self):
        try:
            # Use -version which is standard and check return code
            process = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True, encoding='utf-8', errors='ignore')
            print("FFmpeg found:\n", process.stdout[:100] + "...") # Print first few lines
            return True
        except FileNotFoundError:
            print("FFmpeg command not found.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg command failed: {e}")
            print("Stderr:", e.stderr)
            return False # Or True depending if failure means it exists but has issues
        except Exception as e:
            print(f"Error checking FFmpeg: {e}")
            return False

    def check_ffprobe_installed(self):
        try:
            process = subprocess.run(["ffprobe", "-version"], capture_output=True, check=True, text=True, encoding='utf-8', errors='ignore')
            print("FFprobe found:\n", process.stdout[:100] + "...") # Print first few lines
            return True
        except FileNotFoundError:
            print("FFprobe command not found.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"FFprobe command failed: {e}")
            print("Stderr:", e.stderr)
            return False
        except Exception as e:
            print(f"Error checking FFprobe: {e}")
            return False

    def show_ffmpeg_warning(self, ffmpeg_missing, ffprobe_missing):
        message = ""
        if ffmpeg_missing:
            message += "FFmpeg no está instalado o no se encuentra en la RUTA (PATH) del sistema.\n"
        if ffprobe_missing:
            message += "FFprobe no está instalado o no se encuentra en la RUTA (PATH) del sistema.\n"

        message += "\nAmbos son necesarios para que la aplicación funcione.\n\n"
        message += "Puede descargarlos desde: https://ffmpeg.org/download.html\n\n"
        message += "Asegúrese de que la ubicación de ffmpeg y ffprobe esté incluida en la variable de entorno PATH de su sistema."

        messagebox.showerror(
            "Dependencia Faltante",
            message
        )
        # Disable buttons if dependencies are missing
        self.disable_controls()

    def disable_controls(self):
        self.seleccionar_video_button.config(state="disabled")
        self.seleccionar_salida_button.config(state="disabled")
        self.procesar_button.config(state="disabled")
        self.threshold_entry.config(state="disabled")
        self.duration_entry.config(state="disabled")
        self.bitrate_combobox.config(state="disabled")

    def enable_controls(self):
         # Only enable if dependencies are met
        if self.ffmpeg_installed and self.ffprobe_installed:
            self.seleccionar_video_button.config(state="normal")
            self.seleccionar_salida_button.config(state="normal")
            self.procesar_button.config(state="normal")
            self.threshold_entry.config(state="normal")
            self.duration_entry.config(state="normal")
            self.bitrate_combobox.config(state="normal")
            self.cancelar_button.config(state="disabled") # Cancel disabled initially
        else:
            # Keep disabled if check somehow failed after startup
             self.disable_controls()


    def create_widgets(self):
        # Main frame for better padding and organization
        main_frame = ttk.Frame(self.root, padding="20 20 20 20", style="TFrame")
        main_frame.pack(expand=True, fill="both")
        self.style.configure("TFrame", background="#1e1e1e") # Style the frame bg

        # Configure grid layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0) # Button column fixed size

        row_index = 0

        # --- Input Video ---
        ttk.Label(main_frame, text="Video de Entrada:").grid(row=row_index, column=0, columnspan=2, sticky="w", pady=(0, 5))
        row_index += 1
        self.video_entry = ttk.Entry(main_frame, textvariable=self.video_path, state="readonly")
        self.video_entry.grid(row=row_index, column=0, sticky="ew", padx=(0, 10))
        self.seleccionar_video_button = ttk.Button(main_frame, text="Seleccionar...", command=self.seleccionar_video)
        self.seleccionar_video_button.grid(row=row_index, column=1, sticky="ew")
        row_index += 1

        # --- Output Directory ---
        ttk.Label(main_frame, text="Directorio de Salida:").grid(row=row_index, column=0, columnspan=2, sticky="w", pady=(15, 5))
        row_index += 1
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_path, state="readonly")
        self.output_entry.grid(row=row_index, column=0, sticky="ew", padx=(0, 10))
        self.seleccionar_salida_button = ttk.Button(main_frame, text="Seleccionar...", command=self.seleccionar_salida)
        self.seleccionar_salida_button.grid(row=row_index, column=1, sticky="ew")
        row_index += 1

        # --- Settings Frame ---
        settings_frame = ttk.Frame(main_frame, padding="0 15 0 0", style="TFrame")
        settings_frame.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(20, 0))
        settings_frame.columnconfigure(1, weight=1) # Make entry expand
        row_index += 1

        # --- Silence Threshold ---
        ttk.Label(settings_frame, text="Umbral de Silencio (dB):").grid(row=0, column=0, sticky="w", padx=(0,10), pady=(0, 10))
        self.threshold_entry = ttk.Entry(settings_frame, textvariable=self.silence_threshold, width=10) # Limit width
        self.threshold_entry.grid(row=0, column=1, sticky="w", pady=(0, 10)) # Align left

        # --- Min Silence Duration ---
        ttk.Label(settings_frame, text="Duración Mínima (segundos):").grid(row=1, column=0, sticky="w", padx=(0,10), pady=(0, 10))
        self.duration_entry = ttk.Entry(settings_frame, textvariable=self.min_silence_duration, width=10) # Limit width
        self.duration_entry.grid(row=1, column=1, sticky="w", pady=(0, 10)) # Align left

        # --- Audio Bitrate ---
        ttk.Label(settings_frame, text="Bitrate de Audio (salida):").grid(row=2, column=0, sticky="w", padx=(0,10), pady=(0, 15))
        self.bitrate_combobox = ttk.Combobox(settings_frame, textvariable=self.audio_bitrate,
                                             values=["96k", "128k", "192k", "256k", "320k", "copy"], # Added copy
                                             state="readonly", width=8) # Limit width
        self.bitrate_combobox.grid(row=2, column=1, sticky="w", pady=(0, 15)) # Align left
        self.bitrate_combobox.current(2) # Default to 192k


        # --- Buttons Frame ---
        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.grid(row=row_index, column=0, columnspan=2, pady=(20, 10))
        # Center buttons
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        row_index += 1

        self.procesar_button = ttk.Button(button_frame, text="Procesar Video", command=self.iniciar_proceso, width=15)
        self.procesar_button.grid(row=0, column=0, padx=5)

        self.cancelar_button = ttk.Button(button_frame, text="Cancelar", command=self.cancelar_proceso, width=15)
        self.cancelar_button.grid(row=0, column=1, padx=5)
        self.cancelar_button.config(state="disabled")


        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress_bar.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(10, 5))
        row_index += 1


        # --- Status Label ---
        self.status_label = ttk.Label(main_frame, text="Listo.", anchor="center", justify="center")
        self.status_label.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(5, 10))
        row_index += 1

        # Make the main content area expand
        main_frame.rowconfigure(row_index, weight=1) # Give space below status label

        # Initial state based on checks
        if not self.ffmpeg_installed or not self.ffprobe_installed:
             self.disable_controls()
        else:
             self.enable_controls()


    def seleccionar_video(self):
        # Add more video file types
        filetypes = [
            ("Archivos de Video Comunes", "*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv"),
            ("Todos los archivos", "*.*")
        ]
        file_path = filedialog.askopenfilename(filetypes=filetypes)
        if file_path:
            self.video_path.set(file_path)
            # Auto-suggest output dir based on input video dir
            input_dir = os.path.dirname(file_path)
            if not self.output_path.get(): # Only set if output is empty
                self.output_path.set(input_dir)


    def seleccionar_salida(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_path.set(folder_path)

    def update_status(self, message, processing=False):
        """Helper function to update status label and optionally progress bar"""
        self.status_label.config(text=message)
        if processing:
            if not self.progress_bar.winfo_ismapped(): # Check if visible
                 self.progress_bar.grid() # Make sure it's visible
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            # self.progress_bar.grid_remove() # Hide it when not processing


    def iniciar_proceso(self):
        video_file = self.video_path.get()
        output_dir = self.output_path.get()

        if not video_file or not os.path.isfile(video_file):
            messagebox.showerror("Error", "Por favor, seleccione un archivo de video válido.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Por favor, seleccione un directorio de salida válido.")
            return

        if self.process_running.get():
            messagebox.showinfo("Proceso en Curso", "Ya hay un proceso en ejecución.")
            return

        # Validate numeric inputs
        try:
            threshold_db = float(self.silence_threshold.get()) # Keep as float for validation
            min_duration = float(self.min_silence_duration.get())
            if min_duration <= 0:
                 raise ValueError("La duración mínima debe ser positiva.")
        except ValueError as e:
            messagebox.showerror("Error de Entrada",
                                 f"Valor no válido:\n{e}\n\n"
                                 "Por favor, introduzca valores numéricos válidos.\n"
                                 "Umbral: número (ej: -30)\n"
                                 "Duración: número positivo (ej: 0.5)")
            return

        # --- Prepare for processing ---
        self.process_running.set(True)
        self.procesar_button.config(state="disabled")
        self.cancelar_button.config(state="normal")
        self.disable_controls() # Disable other controls during processing
        self.update_status("Iniciando proceso...", processing=True)

        # Generate unique output filename
        base, ext = os.path.splitext(os.path.basename(video_file))
        # Use timestamp and "_processed" suffix
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base}_processed_{timestamp}{ext}"
        output_file = os.path.join(output_dir, output_filename)

        # --- Start processing thread ---
        # Pass validated/prepared values to the thread function
        self.thread = threading.Thread(
            target=self.procesar_video_thread,
            args=(
                video_file,
                output_file,
                self.silence_threshold.get(), # Pass the string dB value
                min_duration,
                self.audio_bitrate.get()
                )
            )
        self.thread.daemon = True # Allow app to exit even if thread hangs (though cleanup is better)
        self.thread.start()

    def cancelar_proceso(self):
        if self.process_running.get():
            self.update_status("Cancelando...", processing=False)
            self.process_running.set(False) # Signal the thread to stop
            if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                print("Terminating FFmpeg process...")
                try:
                    # Try terminating gracefully first, then kill if needed
                    self.ffmpeg_process.terminate()
                    # Wait a short moment
                    self.ffmpeg_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    print("FFmpeg did not terminate gracefully, killing...")
                    self.ffmpeg_process.kill()
                except Exception as e:
                    print(f"Error terminating/killing FFmpeg: {e}")
                self.ffmpeg_process = None
            # Buttons will be re-enabled by the thread finishing or the check loop

        # Update button states immediately for responsiveness
        self.procesar_button.config(state="normal") # Allow retrying
        self.cancelar_button.config(state="disabled")
        self.enable_controls() # Re-enable config entries


    def procesar_video_thread(self, video_file, output_file, threshold_db_str, min_duration, audio_bitrate_param):
        """Worker thread function for video processing."""
        try:
            # === Step 1: Get Video Duration ===
            self.update_status("Obteniendo duración del video...")
            duration_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_file
            ]
            duration_process = subprocess.run(duration_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if duration_process.returncode != 0 or not duration_process.stdout.strip():
                raise RuntimeError(f"Error al obtener duración del video.\n{duration_process.stderr}")
            video_duration = float(duration_process.stdout.strip())
            print(f"Video duration: {video_duration}s")

            if not self.process_running.get(): return # Check cancellation

            # === Step 2: Detect Silence ===
            self.update_status("Detectando silencio...")
            # Use -f null - for detection only, get info from stderr
            ffmpeg_detect_command = [
                "ffmpeg",
                "-i", video_file,
                "-af", f"silencedetect=noise={threshold_db_str}dB:d={min_duration}",
                "-f", "null", "-"
            ]
            print("Running silence detection:", " ".join(ffmpeg_detect_command))
            detect_process = subprocess.Popen(ffmpeg_detect_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
            self.ffmpeg_process = detect_process # Store for cancellation
            stdout_data, stderr_data = detect_process.communicate()
            self.ffmpeg_process = None # Process finished

            if not self.process_running.get(): return # Check cancellation

            if detect_process.returncode != 0:
                # Even if returncode is non-zero, silencedetect might have printed info
                print(f"FFmpeg silencedetect process finished with code {detect_process.returncode}.")
                # Allow processing to continue if stderr has data, otherwise raise error
                if not stderr_data:
                     raise RuntimeError(f"Error en FFmpeg al detectar silencio.\n{stderr_data}")
                print("Stderr from detection:\n", stderr_data)


            # Parse silence start/end times from STDERR
            silence_start_times = [float(m.group(1)) for m in re.finditer(r'silence_start:\s*(\d+\.?\d*)', stderr_data)]
            silence_end_times = [float(m.group(1)) for m in re.finditer(r'silence_end:\s*(\d+\.?\d*)', stderr_data)]
            print(f"Detected silence starts: {silence_start_times}")
            print(f"Detected silence ends: {silence_end_times}")


            # === Step 3: Calculate Segments to Keep ===
            segments_to_keep = []
            last_end_time = 0.0

            # Handle edge case where detection might start mid-way or end early
            # Ensure we handle the start and end of the video correctly.

            # Correct mismatched lengths if possible (common: last silence runs to end)
            if len(silence_start_times) > len(silence_end_times):
                print("Warning: More silence starts than ends. Assuming last silence extends to video end.")
                silence_end_times.append(video_duration)
            elif len(silence_end_times) > len(silence_start_times):
                 print("Warning: More silence ends than starts. Ignoring extra end times.")
                 silence_end_times = silence_end_times[:len(silence_start_times)]


            for i in range(len(silence_start_times)):
                start = silence_start_times[i]
                end = silence_end_times[i]

                # Clamp start/end times to video duration
                start = max(0.0, start)
                end = min(video_duration, end)

                # Ensure start is before end (handle potential detection glitches)
                if start >= end:
                    print(f"Warning: Skipping invalid silence segment (start >= end): {start} -> {end}")
                    continue

                if start > last_end_time + 0.01: # Add segment before this silence (allow small gap)
                    segments_to_keep.append((last_end_time, start))
                last_end_time = end

            # Add the final segment after the last silence
            if last_end_time < video_duration - 0.01: # Check if there's time left
                segments_to_keep.append((last_end_time, video_duration))

            print(f"Calculated segments to keep: {segments_to_keep}")

            if not self.process_running.get(): return # Check cancellation

            # === Step 4: Handle Cases (No Silence / All Silence / Process) ===
            if not segments_to_keep:
                self.update_status("¡Todo el video parece ser silencio! No se generó salida.")
                # Optionally copy the original or do nothing
                print("No segments to keep. Video might be entirely silent.")
                # Maybe copy if user expects *something*? shutil.copy2(video_file, output_file)
            elif len(segments_to_keep) == 1 and segments_to_keep[0][0] < 0.1 and segments_to_keep[0][1] > video_duration - 0.1:
                # Only one segment covering the whole video (within tolerance) -> No silence detected effectively
                self.update_status("No se detectó silencio significativo. Copiando archivo original...")
                shutil.copy2(video_file, output_file)
                self.update_status(f"Proceso completado (copiado). Salida: {output_file}")
            else:
                # === Step 5: Build the FFmpeg Command for Cutting ===
                self.update_status("Generando video final...")

                # Use select/aselect filters to pick the segments to keep
                # select expression: 'between(t,start1,end1)+between(t,start2,end2)+...'
                select_expr = "+".join([f"between(t,{s:.4f},{e:.4f})" for s, e in segments_to_keep])

                # Filtergraph: select video, select audio, reset timestamps
                # Using N/FRAME_RATE/TB for video and N/SR/TB for audio resets timestamps based on frame/sample count
                # This creates a continuous timeline from the selected segments.
                filter_complex = f"[0:v]select='{select_expr}',setpts=N/FRAME_RATE/TB[v];[0:a]aselect='{select_expr}',asetpts=N/SR/TB[a]"

                ffmpeg_cut_command = [
                    "ffmpeg", "-y", # Overwrite output without asking
                    "-i", video_file,
                    "-filter_complex", filter_complex,
                    "-map", "[v]",  # Map the filtered video stream
                    "-map", "[a]",  # Map the filtered audio stream
                    # Video encoding: Re-encoding is often necessary with select filter
                    # Using libx264 with a decent CRF is a good default
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    # Audio encoding: Use user selection or 'copy' if specified
                    "-c:a", "aac" if audio_bitrate_param != "copy" else "copy",
                ]
                # Add bitrate only if not copying audio
                if audio_bitrate_param != "copy":
                    ffmpeg_cut_command.extend(["-b:a", audio_bitrate_param])

                # Add flags often needed with filtering/segmenting
                ffmpeg_cut_command.extend(["-avoid_negative_ts", "make_zero"])

                ffmpeg_cut_command.append(output_file)

                print("Running final cutting command:", " ".join(ffmpeg_cut_command))

                # === Step 6: Execute the Final Command ===
                cut_process = subprocess.Popen(ffmpeg_cut_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                self.ffmpeg_process = cut_process # Store for cancellation
                stdout_cut, stderr_cut = cut_process.communicate() # Wait for completion
                self.ffmpeg_process = None # Process finished

                if not self.process_running.get(): # Check cancellation *after* communicate
                    # If cancelled during processing, the file might be incomplete, delete it
                    if os.path.exists(output_file):
                        print(f"Process cancelled, removing incomplete file: {output_file}")
                        os.remove(output_file)
                    self.update_status("Proceso Cancelado.")
                    # Button states handled by cancel_proceso
                    return # Exit thread cleanly after cancellation cleanup

                if cut_process.returncode != 0:
                    raise RuntimeError(f"Error en FFmpeg al cortar/unir el video.\nCódigo: {cut_process.returncode}\n{stderr_cut}")
                else:
                    print("FFmpeg final process finished successfully.")
                    print("FFmpeg Output:\n", stderr_cut) # Print ffmpeg logs for debugging
                    self.update_status(f"¡Proceso Completado! Salida: {output_file}")


        except Exception as e:
            error_message = f"¡Error! {type(e).__name__}: {e}"
            print(f"Error during processing: {error_message}")
            # Ensure full error is printed to console for debugging
            import traceback
            traceback.print_exc()
            self.update_status(error_message)
            # Attempt to clean up potentially partial output file on error
            if 'output_file' in locals() and os.path.exists(output_file):
                 try:
                     print(f"Error occurred, removing potentially incomplete file: {output_file}")
                     os.remove(output_file)
                 except OSError as remove_err:
                     print(f"Could not remove partial file: {remove_err}")


        finally:
            # --- Final UI Cleanup (runs whether success, error, or cancel) ---
            self.process_running.set(False)
            # Check if cancelled button needs re-enabling (cancel_proceso might have already done it)
            if self.root.winfo_exists(): # Check if window still exists
                 self.progress_bar.stop()
                 # self.progress_bar.grid_remove() # Hide progress bar
                 self.enable_controls() # Re-enable all controls
                 self.cancelar_button.config(state="disabled") # Disable cancel button
                 self.procesar_button.config(state="normal") # Ensure process button is enabled


    # --- Keep on_close as is ---
    def on_close(self):
        if self.process_running.get():
            if messagebox.askokcancel("Salir", "Hay un proceso en ejecución. ¿Seguro que quieres salir? Esto cancelará el proceso."):
                self.cancelar_proceso() # Attempt graceful cancellation
                # Give cancellation a moment
                if self.thread and self.thread.is_alive():
                    # Don't wait indefinitely, just signal
                    print("Waiting briefly for thread cleanup...")
                    # self.thread.join(timeout=1.0) # Optional short wait
                self.root.destroy()
            else:
                return # Don't close if user cancels the exit confirmation
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
import re
import os # Needed for path manipulation
import shutil # Needed for portable file copying

class VideoEditorApp:
    # Keep the __init__, check_ffmpeg_installed, show_ffmpeg_warning,
    # create_widgets, seleccionar_video, seleccionar_salida,
    # iniciar_proceso, cancelar_proceso, on_close methods AS IS.
    # Only the `procesar_video` method needs significant changes.

    def __init__(self, root):
        self.root = root
        self.root.title("Editor de Video Silencioso")
        self.root.geometry("800x600")
        self.root.configure(bg="#1e1e1e")

        # Estilos personalizados
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TLabel", foreground="#d0d0d0", background="#1e1e1e", font=("Segoe UI", 10))
        self.style.configure("TButton", foreground="#ffffff", background="#4CAF50",
                             font=("Segoe UI", 10), borderwidth=0, relief="flat") # Use flat for modern look
        self.style.map("TButton",
                       foreground=[('active', '#ffffff')],
                       background=[('active', '#388E3C')],
                       relief=[('pressed', 'sunken'), ('!pressed', 'flat')]) # Adjust relief
        self.style.configure("TEntry", foreground="#d0d0d0", background="#2a2a2a", # Lighter foreground for entry
                             font=("Segoe UI", 10), fieldbackground="#2a2a2a",
                             insertbackground="#d0d0d0", # Make cursor visible
                             borderwidth=1, relief="solid") # Add subtle border
        self.style.configure("TProgressbar", background="#4CAF50", troughcolor="#2a2a2a",
                             bordercolor="#2a2a2a", thickness=15) # Make progress bar thicker
        self.style.configure("TCombobox", foreground="#d0d0d0", background="#2a2a2a",
                             fieldbackground="#2a2a2a", selectbackground="#4CAF50",
                             selectforeground="#ffffff", arrowcolor="#d0d0d0",
                             font=("Segoe UI", 10), borderwidth=1, relief="solid")
        self.style.map('TCombobox', fieldbackground=[('readonly', '#2a2a2a')])
        self.style.map('TCombobox', selectbackground=[('readonly', '#4CAF50')])
        self.style.map('TCombobox', selectforeground=[('readonly', '#ffffff')])


        # Variables
        self.video_path = tk.StringVar()
        self.output_path = tk.StringVar()
        # Use dB for threshold, consistent with ffmpeg silencedetect noise=-XXdB format
        self.silence_threshold = tk.StringVar(value="-30") # Default to -30dB, more common starting point
        self.min_silence_duration = tk.DoubleVar(value=0.5) # Default 0.5s
        self.audio_bitrate = tk.StringVar(value="192k") # Default 192k is a good balance
        self.process_running = tk.BooleanVar(value=False)
        self.ffmpeg_process = None # To store the running subprocess instance
        self.thread = None

        # Check FFmpeg FIRST
        self.ffmpeg_installed = self.check_ffmpeg_installed()
        self.ffprobe_installed = self.check_ffprobe_installed()

        # Interfaz de usuario
        self.create_widgets()

        if not self.ffmpeg_installed or not self.ffprobe_installed:
            self.show_ffmpeg_warning(not self.ffmpeg_installed, not self.ffprobe_installed)

    def check_ffmpeg_installed(self):
        try:
            # Use -version which is standard and check return code
            process = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True, encoding='utf-8', errors='ignore')
            print("FFmpeg found:\n", process.stdout[:100] + "...") # Print first few lines
            return True
        except FileNotFoundError:
            print("FFmpeg command not found.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg command failed: {e}")
            print("Stderr:", e.stderr)
            return False # Or True depending if failure means it exists but has issues
        except Exception as e:
            print(f"Error checking FFmpeg: {e}")
            return False

    def check_ffprobe_installed(self):
        try:
            process = subprocess.run(["ffprobe", "-version"], capture_output=True, check=True, text=True, encoding='utf-8', errors='ignore')
            print("FFprobe found:\n", process.stdout[:100] + "...") # Print first few lines
            return True
        except FileNotFoundError:
            print("FFprobe command not found.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"FFprobe command failed: {e}")
            print("Stderr:", e.stderr)
            return False
        except Exception as e:
            print(f"Error checking FFprobe: {e}")
            return False

    def show_ffmpeg_warning(self, ffmpeg_missing, ffprobe_missing):
        message = ""
        if ffmpeg_missing:
            message += "FFmpeg no está instalado o no se encuentra en la RUTA (PATH) del sistema.\n"
        if ffprobe_missing:
            message += "FFprobe no está instalado o no se encuentra en la RUTA (PATH) del sistema.\n"

        message += "\nAmbos son necesarios para que la aplicación funcione.\n\n"
        message += "Puede descargarlos desde: https://ffmpeg.org/download.html\n\n"
        message += "Asegúrese de que la ubicación de ffmpeg y ffprobe esté incluida en la variable de entorno PATH de su sistema."

        messagebox.showerror(
            "Dependencia Faltante",
            message
        )
        # Disable buttons if dependencies are missing
        self.disable_controls()

    def disable_controls(self):
        self.seleccionar_video_button.config(state="disabled")
        self.seleccionar_salida_button.config(state="disabled")
        self.procesar_button.config(state="disabled")
        self.threshold_entry.config(state="disabled")
        self.duration_entry.config(state="disabled")
        self.bitrate_combobox.config(state="disabled")

    def enable_controls(self):
         # Only enable if dependencies are met
        if self.ffmpeg_installed and self.ffprobe_installed:
            self.seleccionar_video_button.config(state="normal")
            self.seleccionar_salida_button.config(state="normal")
            self.procesar_button.config(state="normal")
            self.threshold_entry.config(state="normal")
            self.duration_entry.config(state="normal")
            self.bitrate_combobox.config(state="normal")
            self.cancelar_button.config(state="disabled") # Cancel disabled initially
        else:
            # Keep disabled if check somehow failed after startup
             self.disable_controls()


    def create_widgets(self):
        # Main frame for better padding and organization
        main_frame = ttk.Frame(self.root, padding="20 20 20 20", style="TFrame")
        main_frame.pack(expand=True, fill="both")
        self.style.configure("TFrame", background="#1e1e1e") # Style the frame bg

        # Configure grid layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0) # Button column fixed size

        row_index = 0

        # --- Input Video ---
        ttk.Label(main_frame, text="Video de Entrada:").grid(row=row_index, column=0, columnspan=2, sticky="w", pady=(0, 5))
        row_index += 1
        self.video_entry = ttk.Entry(main_frame, textvariable=self.video_path, state="readonly")
        self.video_entry.grid(row=row_index, column=0, sticky="ew", padx=(0, 10))
        self.seleccionar_video_button = ttk.Button(main_frame, text="Seleccionar...", command=self.seleccionar_video)
        self.seleccionar_video_button.grid(row=row_index, column=1, sticky="ew")
        row_index += 1

        # --- Output Directory ---
        ttk.Label(main_frame, text="Directorio de Salida:").grid(row=row_index, column=0, columnspan=2, sticky="w", pady=(15, 5))
        row_index += 1
        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_path, state="readonly")
        self.output_entry.grid(row=row_index, column=0, sticky="ew", padx=(0, 10))
        self.seleccionar_salida_button = ttk.Button(main_frame, text="Seleccionar...", command=self.seleccionar_salida)
        self.seleccionar_salida_button.grid(row=row_index, column=1, sticky="ew")
        row_index += 1

        # --- Settings Frame ---
        settings_frame = ttk.Frame(main_frame, padding="0 15 0 0", style="TFrame")
        settings_frame.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(20, 0))
        settings_frame.columnconfigure(1, weight=1) # Make entry expand
        row_index += 1

        # --- Silence Threshold ---
        ttk.Label(settings_frame, text="Umbral de Silencio (dB):").grid(row=0, column=0, sticky="w", padx=(0,10), pady=(0, 10))
        self.threshold_entry = ttk.Entry(settings_frame, textvariable=self.silence_threshold, width=10) # Limit width
        self.threshold_entry.grid(row=0, column=1, sticky="w", pady=(0, 10)) # Align left

        # --- Min Silence Duration ---
        ttk.Label(settings_frame, text="Duración Mínima (segundos):").grid(row=1, column=0, sticky="w", padx=(0,10), pady=(0, 10))
        self.duration_entry = ttk.Entry(settings_frame, textvariable=self.min_silence_duration, width=10) # Limit width
        self.duration_entry.grid(row=1, column=1, sticky="w", pady=(0, 10)) # Align left

        # --- Audio Bitrate ---
        ttk.Label(settings_frame, text="Bitrate de Audio (salida):").grid(row=2, column=0, sticky="w", padx=(0,10), pady=(0, 15))
        self.bitrate_combobox = ttk.Combobox(settings_frame, textvariable=self.audio_bitrate,
                                             values=["96k", "128k", "192k", "256k", "320k", "copy"], # Added copy
                                             state="readonly", width=8) # Limit width
        self.bitrate_combobox.grid(row=2, column=1, sticky="w", pady=(0, 15)) # Align left
        self.bitrate_combobox.current(2) # Default to 192k


        # --- Buttons Frame ---
        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.grid(row=row_index, column=0, columnspan=2, pady=(20, 10))
        # Center buttons
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        row_index += 1

        self.procesar_button = ttk.Button(button_frame, text="Procesar Video", command=self.iniciar_proceso, width=15)
        self.procesar_button.grid(row=0, column=0, padx=5)

        self.cancelar_button = ttk.Button(button_frame, text="Cancelar", command=self.cancelar_proceso, width=15)
        self.cancelar_button.grid(row=0, column=1, padx=5)
        self.cancelar_button.config(state="disabled")


        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress_bar.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(10, 5))
        row_index += 1


        # --- Status Label ---
        self.status_label = ttk.Label(main_frame, text="Listo.", anchor="center", justify="center")
        self.status_label.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(5, 10))
        row_index += 1

        # Make the main content area expand
        main_frame.rowconfigure(row_index, weight=1) # Give space below status label

        # Initial state based on checks
        if not self.ffmpeg_installed or not self.ffprobe_installed:
             self.disable_controls()
        else:
             self.enable_controls()


    def seleccionar_video(self):
        # Add more video file types
        filetypes = [
            ("Archivos de Video Comunes", "*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv"),
            ("Todos los archivos", "*.*")
        ]
        file_path = filedialog.askopenfilename(filetypes=filetypes)
        if file_path:
            self.video_path.set(file_path)
            # Auto-suggest output dir based on input video dir
            input_dir = os.path.dirname(file_path)
            if not self.output_path.get(): # Only set if output is empty
                self.output_path.set(input_dir)


    def seleccionar_salida(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_path.set(folder_path)

    def update_status(self, message, processing=False):
        """Helper function to update status label and optionally progress bar"""
        self.status_label.config(text=message)
        if processing:
            if not self.progress_bar.winfo_ismapped(): # Check if visible
                 self.progress_bar.grid() # Make sure it's visible
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            # self.progress_bar.grid_remove() # Hide it when not processing


    def iniciar_proceso(self):
        video_file = self.video_path.get()
        output_dir = self.output_path.get()

        if not video_file or not os.path.isfile(video_file):
            messagebox.showerror("Error", "Por favor, seleccione un archivo de video válido.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Por favor, seleccione un directorio de salida válido.")
            return

        if self.process_running.get():
            messagebox.showinfo("Proceso en Curso", "Ya hay un proceso en ejecución.")
            return

        # Validate numeric inputs
        try:
            threshold_db = float(self.silence_threshold.get()) # Keep as float for validation
            min_duration = float(self.min_silence_duration.get())
            if min_duration <= 0:
                 raise ValueError("La duración mínima debe ser positiva.")
        except ValueError as e:
            messagebox.showerror("Error de Entrada",
                                 f"Valor no válido:\n{e}\n\n"
                                 "Por favor, introduzca valores numéricos válidos.\n"
                                 "Umbral: número (ej: -30)\n"
                                 "Duración: número positivo (ej: 0.5)")
            return

        # --- Prepare for processing ---
        self.process_running.set(True)
        self.procesar_button.config(state="disabled")
        self.cancelar_button.config(state="normal")
        self.disable_controls() # Disable other controls during processing
        self.update_status("Iniciando proceso...", processing=True)

        # Generate unique output filename
        base, ext = os.path.splitext(os.path.basename(video_file))
        # Use timestamp and "_processed" suffix
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base}_processed_{timestamp}{ext}"
        output_file = os.path.join(output_dir, output_filename)

        # --- Start processing thread ---
        # Pass validated/prepared values to the thread function
        self.thread = threading.Thread(
            target=self.procesar_video_thread,
            args=(
                video_file,
                output_file,
                self.silence_threshold.get(), # Pass the string dB value
                min_duration,
                self.audio_bitrate.get()
                )
            )
        self.thread.daemon = True # Allow app to exit even if thread hangs (though cleanup is better)
        self.thread.start()

    def cancelar_proceso(self):
        if self.process_running.get():
            self.update_status("Cancelando...", processing=False)
            self.process_running.set(False) # Signal the thread to stop
            if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                print("Terminating FFmpeg process...")
                try:
                    # Try terminating gracefully first, then kill if needed
                    self.ffmpeg_process.terminate()
                    # Wait a short moment
                    self.ffmpeg_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    print("FFmpeg did not terminate gracefully, killing...")
                    self.ffmpeg_process.kill()
                except Exception as e:
                    print(f"Error terminating/killing FFmpeg: {e}")
                self.ffmpeg_process = None
            # Buttons will be re-enabled by the thread finishing or the check loop

        # Update button states immediately for responsiveness
        self.procesar_button.config(state="normal") # Allow retrying
        self.cancelar_button.config(state="disabled")
        self.enable_controls() # Re-enable config entries


    def procesar_video_thread(self, video_file, output_file, threshold_db_str, min_duration, audio_bitrate_param):
        """Worker thread function for video processing."""
        try:
            # === Step 1: Get Video Duration ===
            self.update_status("Obteniendo duración del video...")
            duration_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_file
            ]
            duration_process = subprocess.run(duration_cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if duration_process.returncode != 0 or not duration_process.stdout.strip():
                raise RuntimeError(f"Error al obtener duración del video.\n{duration_process.stderr}")
            video_duration = float(duration_process.stdout.strip())
            print(f"Video duration: {video_duration}s")

            if not self.process_running.get(): return # Check cancellation

            # === Step 2: Detect Silence ===
            self.update_status("Detectando silencio...")
            # Use -f null - for detection only, get info from stderr
            ffmpeg_detect_command = [
                "ffmpeg",
                "-i", video_file,
                "-af", f"silencedetect=noise={threshold_db_str}dB:d={min_duration}",
                "-f", "null", "-"
            ]
            print("Running silence detection:", " ".join(ffmpeg_detect_command))
            detect_process = subprocess.Popen(ffmpeg_detect_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
            self.ffmpeg_process = detect_process # Store for cancellation
            stdout_data, stderr_data = detect_process.communicate()
            self.ffmpeg_process = None # Process finished

            if not self.process_running.get(): return # Check cancellation

            if detect_process.returncode != 0:
                # Even if returncode is non-zero, silencedetect might have printed info
                print(f"FFmpeg silencedetect process finished with code {detect_process.returncode}.")
                # Allow processing to continue if stderr has data, otherwise raise error
                if not stderr_data:
                     raise RuntimeError(f"Error en FFmpeg al detectar silencio.\n{stderr_data}")
                print("Stderr from detection:\n", stderr_data)


            # Parse silence start/end times from STDERR
            silence_start_times = [float(m.group(1)) for m in re.finditer(r'silence_start:\s*(\d+\.?\d*)', stderr_data)]
            silence_end_times = [float(m.group(1)) for m in re.finditer(r'silence_end:\s*(\d+\.?\d*)', stderr_data)]
            print(f"Detected silence starts: {silence_start_times}")
            print(f"Detected silence ends: {silence_end_times}")


            # === Step 3: Calculate Segments to Keep ===
            segments_to_keep = []
            last_end_time = 0.0

            # Handle edge case where detection might start mid-way or end early
            # Ensure we handle the start and end of the video correctly.

            # Correct mismatched lengths if possible (common: last silence runs to end)
            if len(silence_start_times) > len(silence_end_times):
                print("Warning: More silence starts than ends. Assuming last silence extends to video end.")
                silence_end_times.append(video_duration)
            elif len(silence_end_times) > len(silence_start_times):
                 print("Warning: More silence ends than starts. Ignoring extra end times.")
                 silence_end_times = silence_end_times[:len(silence_start_times)]


            for i in range(len(silence_start_times)):
                start = silence_start_times[i]
                end = silence_end_times[i]

                # Clamp start/end times to video duration
                start = max(0.0, start)
                end = min(video_duration, end)

                # Ensure start is before end (handle potential detection glitches)
                if start >= end:
                    print(f"Warning: Skipping invalid silence segment (start >= end): {start} -> {end}")
                    continue

                if start > last_end_time + 0.01: # Add segment before this silence (allow small gap)
                    segments_to_keep.append((last_end_time, start))
                last_end_time = end

            # Add the final segment after the last silence
            if last_end_time < video_duration - 0.01: # Check if there's time left
                segments_to_keep.append((last_end_time, video_duration))

            print(f"Calculated segments to keep: {segments_to_keep}")

            if not self.process_running.get(): return # Check cancellation

            # === Step 4: Handle Cases (No Silence / All Silence / Process) ===
            if not segments_to_keep:
                self.update_status("¡Todo el video parece ser silencio! No se generó salida.")
                # Optionally copy the original or do nothing
                print("No segments to keep. Video might be entirely silent.")
                # Maybe copy if user expects *something*? shutil.copy2(video_file, output_file)
            elif len(segments_to_keep) == 1 and segments_to_keep[0][0] < 0.1 and segments_to_keep[0][1] > video_duration - 0.1:
                # Only one segment covering the whole video (within tolerance) -> No silence detected effectively
                self.update_status("No se detectó silencio significativo. Copiando archivo original...")
                shutil.copy2(video_file, output_file)
                self.update_status(f"Proceso completado (copiado). Salida: {output_file}")
            else:
                # === Step 5: Build the FFmpeg Command for Cutting ===
                self.update_status("Generando video final...")

                # Use select/aselect filters to pick the segments to keep
                # select expression: 'between(t,start1,end1)+between(t,start2,end2)+...'
                select_expr = "+".join([f"between(t,{s:.4f},{e:.4f})" for s, e in segments_to_keep])

                # Filtergraph: select video, select audio, reset timestamps
                # Using N/FRAME_RATE/TB for video and N/SR/TB for audio resets timestamps based on frame/sample count
                # This creates a continuous timeline from the selected segments.
                filter_complex = f"[0:v]select='{select_expr}',setpts=N/FRAME_RATE/TB[v];[0:a]aselect='{select_expr}',asetpts=N/SR/TB[a]"

                ffmpeg_cut_command = [
                    "ffmpeg", "-y", # Overwrite output without asking
                    "-i", video_file,
                    "-filter_complex", filter_complex,
                    "-map", "[v]",  # Map the filtered video stream
                    "-map", "[a]",  # Map the filtered audio stream
                    # Video encoding: Re-encoding is often necessary with select filter
                    # Using libx264 with a decent CRF is a good default
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    # Audio encoding: Use user selection or 'copy' if specified
                    "-c:a", "aac" if audio_bitrate_param != "copy" else "copy",
                ]
                # Add bitrate only if not copying audio
                if audio_bitrate_param != "copy":
                    ffmpeg_cut_command.extend(["-b:a", audio_bitrate_param])

                # Add flags often needed with filtering/segmenting
                ffmpeg_cut_command.extend(["-avoid_negative_ts", "make_zero"])

                ffmpeg_cut_command.append(output_file)

                print("Running final cutting command:", " ".join(ffmpeg_cut_command))

                # === Step 6: Execute the Final Command ===
                cut_process = subprocess.Popen(ffmpeg_cut_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                self.ffmpeg_process = cut_process # Store for cancellation
                stdout_cut, stderr_cut = cut_process.communicate() # Wait for completion
                self.ffmpeg_process = None # Process finished

                if not self.process_running.get(): # Check cancellation *after* communicate
                    # If cancelled during processing, the file might be incomplete, delete it
                    if os.path.exists(output_file):
                        print(f"Process cancelled, removing incomplete file: {output_file}")
                        os.remove(output_file)
                    self.update_status("Proceso Cancelado.")
                    # Button states handled by cancel_proceso
                    return # Exit thread cleanly after cancellation cleanup

                if cut_process.returncode != 0:
                    raise RuntimeError(f"Error en FFmpeg al cortar/unir el video.\nCódigo: {cut_process.returncode}\n{stderr_cut}")
                else:
                    print("FFmpeg final process finished successfully.")
                    print("FFmpeg Output:\n", stderr_cut) # Print ffmpeg logs for debugging
                    self.update_status(f"¡Proceso Completado! Salida: {output_file}")


        except Exception as e:
            error_message = f"¡Error! {type(e).__name__}: {e}"
            print(f"Error during processing: {error_message}")
            # Ensure full error is printed to console for debugging
            import traceback
            traceback.print_exc()
            self.update_status(error_message)
            # Attempt to clean up potentially partial output file on error
            if 'output_file' in locals() and os.path.exists(output_file):
                 try:
                     print(f"Error occurred, removing potentially incomplete file: {output_file}")
                     os.remove(output_file)
                 except OSError as remove_err:
                     print(f"Could not remove partial file: {remove_err}")


        finally:
            # --- Final UI Cleanup (runs whether success, error, or cancel) ---
            self.process_running.set(False)
            # Check if cancelled button needs re-enabling (cancel_proceso might have already done it)
            if self.root.winfo_exists(): # Check if window still exists
                 self.progress_bar.stop()
                 # self.progress_bar.grid_remove() # Hide progress bar
                 self.enable_controls() # Re-enable all controls
                 self.cancelar_button.config(state="disabled") # Disable cancel button
                 self.procesar_button.config(state="normal") # Ensure process button is enabled


    # --- Keep on_close as is ---
    def on_close(self):
        if self.process_running.get():
            if messagebox.askokcancel("Salir", "Hay un proceso en ejecución. ¿Seguro que quieres salir? Esto cancelará el proceso."):
                self.cancelar_proceso() # Attempt graceful cancellation
                # Give cancellation a moment
                if self.thread and self.thread.is_alive():
                    # Don't wait indefinitely, just signal
                    print("Waiting briefly for thread cleanup...")
                    # self.thread.join(timeout=1.0) # Optional short wait
                self.root.destroy()
            else:
                return # Don't close if user cancels the exit confirmation
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
