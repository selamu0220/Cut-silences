import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import soundfile as sf
import numpy as np
from scipy import signal as nr


class AudioEnhancerPro:
    def __init__(self, root):
        self.root = root
        self.root.title("🎙️ Audio Enhancer Pro Studio")
        self.root.geometry('600x450')
        self.audio_path = None
        self.final_audio = None
        self.sr = None

        # Parámetros de procesamiento predeterminados
        self.processing_params = {
            'gain': 1.0,
            'bass_boost': 2.0,
            'treble_boost': 1.5,
            'compression': 0.7,
            'presence': 1.3,
            'stereo_mode': True  # Nuevo parámetro para control stereo
        }

        self.root.configure(bg='white')
        self.style_config()
        self.create_gui()

    def style_config(self):
        self.button_style = {
            'bg': '#2D2D2D',
            'fg': 'white',
            'font': ('Arial', 10, 'bold'),
            'padx': 20,
            'pady': 5,
            'relief': 'flat',
            'cursor': 'hand2',
            'activebackground': '#404040',
            'activeforeground': 'white'
        }

    def create_gui(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)

        tk.Label(
            main_frame,
            text="🎙️ Audio Enhancer Pro Studio",
            font=('Arial', 18, 'bold'),
            bg='white',
            fg='#2D2D2D'
        ).pack(pady=10)

        self.create_controls(main_frame)

    def create_controls(self, parent):
        # Frame para controles
        self.controls_frame = tk.Frame(parent, bg='white')
        self.controls_frame.pack(pady=10)

        # Controles deslizantes
        sliders = [
            ("Ganancia", 'gain', 0.0, 2.0),
            ("Refuerzo de Graves", 'bass_boost', 0.0, 4.0),
            ("Refuerzo de Agudos", 'treble_boost', 0.0, 3.0),
            ("Compresión", 'compression', 0.0, 1.0),
            ("Presencia", 'presence', 0.0, 2.0)
        ]

        for label_text, param, min_val, max_val in sliders:
            frame = tk.Frame(self.controls_frame, bg='white')
            frame.pack(pady=5)

            tk.Label(
                frame,
                text=label_text,
                bg='white',
                fg='#2D2D2D',
                font=('Arial', 10)
            ).pack(side='left', padx=10)

            slider = ttk.Scale(
                frame,
                from_=min_val,
                to=max_val,
                value=self.processing_params[param],
                orient='horizontal',
                length=200,
                command=lambda v, p=param: self.update_param(p, float(v))
            )
            slider.pack(side='left', padx=10)

        # Control Mono/Stereo
        stereo_frame = tk.Frame(self.controls_frame, bg='white')
        stereo_frame.pack(pady=5)

        tk.Label(
            stereo_frame,
            text="Modo de Audio",
            bg='white',
            fg='#2D2D2D',
            font=('Arial', 10)
        ).pack(side='left', padx=10)

        self.stereo_var = tk.BooleanVar(value=True)
        stereo_check = ttk.Checkbutton(
            stereo_frame,
            text="Stereo",
            variable=self.stereo_var,
            command=lambda: self.update_param('stereo_mode', self.stereo_var.get())
        )
        stereo_check.pack(side='left', padx=10)

        # Botones
        button_frame = tk.Frame(parent, bg='white')
        button_frame.pack(pady=20)

        self.select_button = tk.Button(
            button_frame,
            text="Seleccionar Audio",
            command=self.select_file,
            **self.button_style
        )
        self.select_button.pack(side='left', padx=5)

        self.process_button = tk.Button(
            button_frame,
            text="Procesar",
            command=self.start_processing,
            state='disabled',
            **self.button_style
        )
        self.process_button.pack(side='left', padx=5)

        self.save_button = tk.Button(
            button_frame,
            text="Guardar",
            command=self.save_audio,
            state='disabled',
            **self.button_style
        )
        self.save_button.pack(side='left', padx=5)

        # Barra de progreso
        self.progress = ttk.Progressbar(
            parent,
            orient='horizontal',
            length=300,
            mode='determinate'
        )
        self.progress.pack(pady=10)

        # Etiqueta de estado
        self.status_label = tk.Label(
            parent,
            text="Estado: Esperando archivo...",
            bg='white',
            fg='#2D2D2D',
            font=('Arial', 10)
        )
        self.status_label.pack(pady=5)

    def update_param(self, param, value):
        self.processing_params[param] = value

    def apply_professional_enhancement(self, audio_data):
        # Aplicar ganancia
        audio_data = audio_data * self.processing_params['gain']

        # Refuerzo de graves (filtro paso bajo)
        b, a = nr.butter(4, 150 / (self.sr / 2), btype='lowpass')
        bass = nr.lfilter(b, a, audio_data)
        audio_data = audio_data + (bass * (self.processing_params['bass_boost'] - 1))

        # Refuerzo de agudos (filtro paso alto)
        b, a = nr.butter(4, 4000 / (self.sr / 2), btype='highpass')
        treble = nr.lfilter(b, a, audio_data)
        audio_data = audio_data + (treble * (self.processing_params['treble_boost'] - 1))

        # Compresión
        audio_data = self.apply_compression(audio_data)

        # Mejora de presencia
        audio_data = self.enhance_presence(audio_data)

        return np.clip(audio_data, -1, 1)

    def apply_compression(self, audio_data):
        threshold = 0.3
        ratio = 4 + (self.processing_params['compression'] * 6)

        # Compresión básica
        magnitude = np.abs(audio_data)
        compressed = np.copy(audio_data)
        mask = magnitude > threshold
        compressed[mask] = (
                                   threshold +
                                   (magnitude[mask] - threshold) / ratio
                           ) * np.sign(audio_data[mask])

        return compressed

    def enhance_presence(self, audio_data):
        # Filtro de presencia (2-4 kHz)
        b, a = nr.butter(2, [2000 / (self.sr / 2), 4000 / (self.sr / 2)], btype='bandpass')
        presence = nr.lfilter(b, a, audio_data)

        # Ajustar la cantidad de presencia
        enhanced = audio_data + (presence * (self.processing_params['presence'] - 1))

        return enhanced

    def select_file(self):
        try:
            self.audio_path = filedialog.askopenfilename(
                filetypes=[
                    ("Archivos de audio", "*.wav *.mp3 *.flac *.ogg"),
                    ("Todos los archivos", "*.*")
                ]
            )

            if self.audio_path:
                self.status_label.config(
                    text=f"Archivo seleccionado: {self.audio_path.split('/')[-1]}"
                )
                self.process_button.config(state='normal')
                self.save_button.config(state='disabled')
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al seleccionar el archivo: {str(e)}"
            )

    def update_progress(self, value):
        self.progress['value'] = value
        self.root.update_idletasks()

    def process_audio(self):
        try:
            self.status_label.config(text="Procesando audio...")
            self.update_progress(20)

            # Cargar archivo
            audio_data, self.sr = sf.read(self.audio_path)
            self.update_progress(40)

            # Manejar canales según el modo seleccionado
            if len(audio_data.shape) > 1:  # Si es stereo
                if self.processing_params['stereo_mode']:
                    # Procesar cada canal por separado
                    left_channel = self.apply_professional_enhancement(audio_data[:, 0])
                    right_channel = self.apply_professional_enhancement(audio_data[:, 1])
                    self.final_audio = np.column_stack((left_channel, right_channel))
                else:
                    # Convertir a mono
                    audio_data = np.mean(audio_data, axis=1)
                    self.final_audio = self.apply_professional_enhancement(audio_data)
            else:  # Si es mono
                if self.processing_params['stereo_mode']:
                    # Convertir mono a stereo
                    processed = self.apply_professional_enhancement(audio_data)
                    self.final_audio = np.column_stack((processed, processed))
                else:
                    self.final_audio = self.apply_professional_enhancement(audio_data)

            self.update_progress(80)
            self.status_label.config(text="¡Procesamiento completado!")
            self.save_button.config(state='normal')
            self.update_progress(100)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error durante el procesamiento: {str(e)}"
            )
            self.status_label.config(text="Error durante el procesamiento")
        finally:
            self.update_progress(0)

    def start_processing(self):
        if self.audio_path:
            self.process_audio()
        else:
            messagebox.showwarning(
                "Advertencia",
                "Por favor, seleccione un archivo de audio primero"
            )

    def save_audio(self):
        if self.final_audio is not None:
            try:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".wav",
                    filetypes=[("Archivo WAV", "*.wav")]
                )

                if save_path:
                    self.status_label.config(text="Guardando archivo...")
                    self.update_progress(50)

                    sf.write(
                        save_path,
                        self.final_audio,
                        self.sr
                    )

                    self.update_progress(100)
                    self.status_label.config(
                        text=f"Archivo guardado como: {save_path.split('/')[-1]}"
                    )
                    messagebox.showinfo(
                        "Éxito",
                        "Archivo guardado correctamente"
                    )

            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Error al guardar el archivo: {str(e)}"
                )
            finally:
                self.update_progress(0)
        else:
            messagebox.showwarning(
                "Advertencia",
                "No hay audio procesado para guardar"
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioEnhancerPro(root)
    root.mainloop()
