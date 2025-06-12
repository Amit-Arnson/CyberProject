import base64
import pprint
import time

import asyncio
import flet as ft
import aiofiles

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from GUI.Controls.navigation_sidebar import NavigationSidebar
from Utils.format import format_length_from_milliseconds

from pseudo_http_protocol import ClientMessage

from MediaHandling.audio_information import decode_audio_bytes

import librosa
import numpy as np


class AudioInformation:
    CHROMA_LABELS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    SCALE_DEFINITIONS = {
        'C Major': {'C', 'D', 'E', 'F', 'G', 'A', 'B'},
        'A Minor': {'A', 'B', 'C', 'D', 'E', 'F', 'G'},
        'G Major': {'G', 'A', 'B', 'C', 'D', 'E', 'F#'},
        'E Minor': {'E', 'F#', 'G', 'A', 'B', 'C', 'D'},
        'D Major': {'D', 'E', 'F#', 'G', 'A', 'B', 'C#'},
        'B Minor': {'B', 'C#', 'D', 'E', 'F#', 'G', 'A'},
        'F Major': {'F', 'G', 'A', 'A#', 'C', 'D', 'E'},
        'Bb Major': {'A#', 'C', 'D', 'D#', 'F', 'G', 'A'},
        'E Major': {'E', 'F#', 'G#', 'A', 'B', 'C#', 'D#'},
        'A Major': {'A', 'B', 'C#', 'D', 'E', 'F#', 'G#'},
        'D Minor': {'D', 'E', 'F', 'G', 'A', 'A#', 'C'},
        'E Minor Pentatonic': {'E', 'G', 'A', 'B', 'D'},
        'A Minor Pentatonic': {'A', 'C', 'D', 'E', 'G'},

        # Modes
        'D Dorian': {'D', 'E', 'F', 'G', 'A', 'B', 'C'},
        'E Phrygian': {'E', 'F', 'G', 'A', 'B', 'C', 'D'},
        'F Lydian': {'F', 'G', 'A', 'B', 'C', 'D', 'E'},
        'G Mixolydian': {'G', 'A', 'B', 'C', 'D', 'E', 'F'},
        'A Aeolian': {'A', 'B', 'C', 'D', 'E', 'F', 'G'},
        'B Locrian': {'B', 'C', 'D', 'E', 'F', 'G', 'A'},
    }

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # these sizes are the optimal ratio for the average PC screen
        self.page_width = 1280
        self.page_height = 720

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

        self.user_cache: ClientSideUserCache | None = None
        if hasattr(page, "user_cache"):
            self.user_cache: ClientSideUserCache = page.user_cache

        self.sidebar = NavigationSidebar(page=page)
        # override the on_click method so that clicking on the button does not reset the information already input
        self.sidebar.goto_tempo_finder.on_click = None

        # the sidebar is set to 2 and the right side of the page is set to 10. this means the sidebar takes 20% of the
        # available screen
        self.sidebar.expand = 2

        self.audio_bytes: bytes = b""
        self.is_currently_extracting_information: bool = False

        self.audio_file_selector = ft.FilePicker(on_result=self._load_local_audio_bytes)

        self.page.overlay.append(self.audio_file_selector)

        self.loading_overlay_bar = ft.ProgressBar(
            width=150,
            height=20,
            value=0.01
        )

        self.loading_overlay = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Extracting information"),
                    self.loading_overlay_bar
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            alignment=ft.Alignment(0, 0)
        )

        self.downloading_song_bytes_overlay = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        ft.Text("Downloading Audio"),
                        alignment=ft.Alignment(0, 0)
                    ),
                    ft.Container(
                        ft.ProgressRing(),
                        alignment=ft.Alignment(0, 0)
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            alignment=ft.Alignment(0, 0)
        )

        self._initialize_controls()

    def add_search_results(self, songs: list[dict[str, str]]):
        song_containers = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(song_info["name"], size=30, color=ft.Colors.GREY_400),
                        ft.Column(
                            [
                                ft.Text(song_info["album"], color=ft.Colors.GREY_400, size=15, ),
                                ft.Text(song_info["artist"], color=ft.Colors.GREY_600, size=10,),
                            ],
                            spacing=0,
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ]
                ),
                data=song_info["song_id"],
                height=75,
                expand_loose=True,
                bgcolor=ft.Colors.GREY_200,
                border_radius=10,
                padding=10,
                on_click=self._request_song_bytes
            )
            for song_info in songs
        ]

        self.search_values.controls = song_containers

        self.search_values.update()

    def _request_song_bytes(self, event: ft.ControlEvent):
        # reset the current buffered bytes
        self.audio_bytes = b""

        song_id: int = event.control.data

        self._add_downloading_audio_screen()

        self.page.close(self.search_popup)

        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="get",
                endpoint="song/download/audio",
                payload={
                    "song_id": song_id
                }
            ).encode()
        )

    async def add_song_bytes(
            self,
            song_id: int,
            file_id: str,
            b64_chunk: str,
            is_last_chunk: bool
    ):
        byte_chunk = base64.b64decode(b64_chunk)

        self.audio_bytes += byte_chunk

        if is_last_chunk:
            self._remove_downloading_audio_screen()

            if not self.is_currently_extracting_information:

                self._add_loading_screen()

                if self.audio_bytes:
                    sample, sample_rate = await decode_audio_bytes(self.audio_bytes)

                    await self._increase_loading_process(0.1)

                    await self._extract_mir_features(sample, sample_rate)

                    self.page.update()

                self._remove_loading_screen()

    def _add_loading_screen(self):
        self.loading_overlay_bar.value = 0.01
        self.page.overlay.append(self.loading_overlay)

        self.page.update()

    def _remove_loading_screen(self):
        self.loading_overlay_bar.value = 0.01
        self.page.overlay.remove(self.loading_overlay)

        self.page.update()

    def _add_downloading_audio_screen(self):
        self.page.overlay.append(self.downloading_song_bytes_overlay)

        self.page.update()

    def _remove_downloading_audio_screen(self):
        self.page.overlay.remove(self.downloading_song_bytes_overlay)

        self.page.update()

    async def _increase_loading_process(self, amount: float):
        amount = amount / 10
        for _ in range(10):
            self.loading_overlay_bar.value += amount

            self.loading_overlay_bar.update()

            await asyncio.sleep(0.05)

    async def _load_local_audio_bytes(self, event: ft.FilePickerResultEvent):
        file = event.files
        if not file:
            return

        file_path: str = file[0].path

        if not self.is_currently_extracting_information:

            self._add_loading_screen()

            async with aiofiles.open(file_path, "rb") as file:
                self.audio_bytes = await file.read()

            if self.audio_bytes:
                sample, sample_rate = await decode_audio_bytes(self.audio_bytes)

                await self._increase_loading_process(0.1)

                await self._extract_mir_features(sample, sample_rate)

                self.page.update()

            self._remove_loading_screen()

    @staticmethod
    def _smart_round(value: float) -> float | int:
        # Round to nearest int if close, else 1 decimal place
        if abs(value - round(value)) < 0.05:
            return int(round(value))

        return round(value, 1)

    def _detect_scale_from_chroma(self, chroma_mean: list, top_n: int = 7) -> str:
        chroma_array = np.array(chroma_mean)
        top_indices = chroma_array.argsort()[-top_n:][::-1]
        detected_notes = {self.CHROMA_LABELS[i] for i in top_indices}

        best_match = None
        max_overlap = 0

        for scale_name, scale_notes in self.SCALE_DEFINITIONS.items():
            overlap = len(detected_notes & scale_notes)
            if overlap > max_overlap:
                max_overlap = overlap
                best_match = scale_name

        return best_match if best_match else "Unknown"

    @staticmethod
    def _label_energy(value):
        if value < 0.40:
            return "low"
        elif value < 0.46:
            return "moderate"
        else:
            return "high"

    async def _extract_mir_features(self, sample: np.ndarray, sample_rate: int):
        self.is_currently_extracting_information = True

        print("started extracting")
        loop = self.page.loop

        try:
            # Tempo and beat tracking
            tempo, beats = await loop.run_in_executor(
                None,
                lambda: librosa.beat.beat_track(y=sample, sr=sample_rate)
            )

            average_tempo = self._smart_round(float(tempo.item()))

            # 1. Onset envelope for tracking local energy peaks
            onset_env = await loop.run_in_executor(
                None,
                lambda: librosa.onset.onset_strength(y=sample, sr=sample_rate, hop_length=512)
            )

            # 3. Convert frames to BPM
            local_tempi = await loop.run_in_executor(
                None,
                lambda: librosa.feature.rhythm.tempo(onset_envelope=onset_env, sr=sample_rate, hop_length=512,
                                                     aggregate=None)
            )

            # 4. Times associated with each local tempo
            tempogram_times = await loop.run_in_executor(
                None,
                lambda: librosa.frames_to_time(np.arange(len(local_tempi)), sr=sample_rate, hop_length=512)
            )

            self._set_local_tempo_chart(
                tempi=local_tempi,
                tempi_times=tempogram_times,
                update=False
            )

            await self._increase_loading_process(0.2)

            duration = await loop.run_in_executor(
                None,
                lambda: librosa.get_duration(y=sample, sr=sample_rate)
            )

            self._set_duration(
                duration_seconds=duration,
                update=False
            )

            await self._increase_loading_process(0.2)

            # Compute RMS (Root Mean Square energy)
            rms = await loop.run_in_executor(
                None,
                lambda: librosa.feature.rms(y=sample, hop_length=512)[0]
            )

            frames = range(len(rms))

            times = await loop.run_in_executor(
                None,
                lambda: librosa.frames_to_time(frames, sr=sample_rate, hop_length=512)
            )

            self._set_rms_chart(
                rms=rms,
                rms_times=times,
                update=False
            )

            await self._increase_loading_process(0.3)

            # Chroma feature (pitch class energy)
            chroma = await loop.run_in_executor(
                None,
                lambda: librosa.feature.chroma_stft(y=sample, sr=sample_rate)
            )

            chroma_mean = chroma.mean(axis=1).tolist()
            detected_scale = self._detect_scale_from_chroma(chroma_mean)

            chroma_label_information = []
            for note, value in zip(self.CHROMA_LABELS, chroma_mean):
                label = self._label_energy(value)
                chroma_label_information.append(f"{note:<3} - {value:.3f} ({label})")

            self._set_chroma_values(
                chroma_label_information,
                detected_scale,
                update=False
            )

            await self._increase_loading_process(0.3)

            self.is_currently_extracting_information = False
        except Exception as e:
            print(e)

            self.is_currently_extracting_information = False

    def _set_duration(self, duration_seconds: int, update: bool = True):
        duration_milliseconds = round(duration_seconds * 1000)

        duration_string = format_length_from_milliseconds(duration_milliseconds)

        self.duration_box.content = ft.Text(f"{duration_string}", color=ft.Colors.GREY_400, size=30)

        if update:
            self.duration_box.update()

    def _set_rms_chart(self, rms, rms_times, update: bool = True):
        data_points = [
            ft.LineChartDataPoint(x, y)
            for x, y in zip(rms_times, rms)
        ]

        data_series = [
            ft.LineChartData(
                data_points=data_points,
                stroke_width=4,
                color=ft.Colors.GREY_400,
                curved=True,
            )
        ]

        chart = ft.LineChart(
            data_series=data_series,
            min_x=min(rms_times),
            max_x=max(rms_times),
            min_y=0,
            max_y=max(rms) * 1.1,  # small buffer above peak
            expand=True,
            tooltip_bgcolor=ft.Colors.BLUE_GREY,
            tooltip_fit_inside_horizontally=True,
            tooltip_fit_inside_vertically=True,
        )

        self.rms_box.content = chart

        if update:
            self.rms_box.update()

    def _set_local_tempo_chart(self, tempi, tempi_times, update: bool = True):
        data_points = [
            ft.LineChartDataPoint(round(x), self._smart_round(y))
            for x, y in zip(tempi_times, tempi)
        ]

        data_series = [
            ft.LineChartData(
                data_points=data_points,
                stroke_width=4,
                color=ft.Colors.GREY_400,
                curved=True,
            )
        ]

        chart = ft.LineChart(
            data_series=data_series,
            min_x=min(tempi_times),
            max_x=max(tempi_times),
            min_y=min(tempi) * 0.9,  # small buffer below
            max_y=max(tempi) * 1.1,  # small buffer above
            expand=True,
            tooltip_bgcolor=ft.Colors.BLUE_GREY,
            tooltip_fit_inside_horizontally=True,
            tooltip_fit_inside_vertically=True,
        )

        self.tempo_box.content = chart

        if update:
            self.tempo_box.update()

    def _set_chroma_values(self, chroma_labels: list[str], detected_key: str, update: bool = True):
        chroma_info = ft.Column(
            [
                ft.Text(f"Detected key: {detected_key}", color=ft.Colors.GREY_400),
                *(ft.Text(label, color=ft.Colors.GREY_400) for label in chroma_labels)
            ]
        )

        self.chroma_box.content = chroma_info

        if update:
            self.chroma_box.update()

    def _select_audio_files(self, e: ft.ControlEvent):
        self.audio_file_selector.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.AUDIO
        )

    def _request_song_info(self, name: str = ""):
        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                endpoint="song/search",
                method="get",
                payload={
                    "name": name
                }
            ).encode()
        )

    def _searchbar_change(self, event: ft.ControlEvent):
        self._request_song_info(name=event.data)

    def _initialize_file_selectors(self):
        self.song_selector = ft.Container(
            content=ft.Text("Upload Local File", color=ft.Colors.GREY_800),
            on_click=self._select_audio_files,
            width=150,
            height=50,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=15,
            alignment=ft.Alignment(0, 0)
        )

    def _initialize_searchbar(self):
        self.search_values = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START
        )

        search_bar = ft.Container(
            ft.Row(
                [
                    ft.Icon(ft.Icons.SEARCH_ROUNDED, color=ft.Colors.GREY_600),
                    ft.VerticalDivider(),
                    ft.TextField(
                        expand=True,
                        on_change=self._searchbar_change,
                        autofocus=True,
                        border=ft.InputBorder.NONE
                    ),
                ]
            ),
            padding=ft.Padding(
                left=10,
                right=10,
                top=0,
                bottom=0
            ),
            height=50,
            border_radius=15,
            border=ft.border.all(1, color=ft.Colors.BLACK)
        )

        self.search_popup = ft.AlertDialog(
            content=ft.Container(
                ft.Column(
                    [
                        search_bar,
                        self.search_values
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
                width=500,
                height=550
            )
        )

        self.searchbar = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.SEARCH_ROUNDED, color=ft.Colors.GREY_600),
                    ft.VerticalDivider()
                ]
            ),
            padding=10,
            height=50,
            expand=True,
            border_radius=15,
            border=ft.border.all(1, color=ft.Colors.BLACK),
            on_click=self._open_search_popup
        )

    def _open_search_popup(self, *args):
        self.page.open(self.search_popup)

        self._request_song_info()

    def _initialize_duration_box(self):
        self.duration_box: ft.Container = ft.Container(
            content=ft.Text("XX:XX", color=ft.Colors.GREY_400, size=30),
            bgcolor=ft.Colors.GREY_600,
            border_radius=10,
            width=175,
            height=120,
            padding=10,
            alignment=ft.Alignment(0, 0)
        )

        self.diration_display = ft.Column(
            [
                ft.Text("duration"),
                self.duration_box
            ],
            width=175,
            height=150,
        )

    def _initialize_tempo_box(self):
        tempi = [100, 151, 102, 101, 101, 101]
        tempi_times = [1, 2, 3, 4, 5, 6]
        data_points = [
            ft.LineChartDataPoint(round(x), self._smart_round(y))
            for x, y in zip(tempi_times, tempi)
        ]

        data_series = [
            ft.LineChartData(
                data_points=data_points,
                stroke_width=4,
                color=ft.Colors.GREY_400,
                curved=True,
            )
        ]

        chart = ft.LineChart(
            data_series=data_series,
            min_x=min(tempi_times),
            max_x=max(tempi_times),
            min_y=min(tempi) * 0.9,  # small buffer below
            max_y=max(tempi) * 1.1,  # small buffer above
            expand=True,
            tooltip_bgcolor=ft.Colors.BLUE_GREY,
            tooltip_fit_inside_horizontally=True,
            tooltip_fit_inside_vertically=True,
        )

        self.tempo_box: ft.Container = ft.Container(
            content=chart,
            bgcolor=ft.Colors.GREY_600,
            border_radius=10,
            expand=True,
            height=150,
            padding=10
        )

        self.tempo_display = ft.Column(
            [
                ft.Text("Tempo over time"),
                self.tempo_box
            ],
            expand=True,
            height=150,
        )

    def _initialize_chroma_box(self):
        self.chroma_box: ft.Container = ft.Container(
            content=ft.Column(
                [
                    ft.Text(chroma_key, color=ft.Colors.GREY_400) for chroma_key in self.CHROMA_LABELS
                ]
            ),
            bgcolor=ft.Colors.GREY_600,
            border_radius=10,
            width=175,
            height=370,
            padding=10
        )

        self.chroma_display: ft.Column = ft.Column(
            [
                ft.Text("Chroma keys & scale"),
                self.chroma_box
            ],
            width=175,
            height=400,
        )

    def _initialize_rms_values_box(self):
        rms_times = [i for i in range(30)]  # 30 time steps (e.g., seconds or frames)
        rms_values = [
            0.03, 0.12, 0.18, 0.24, 0.33, 0.42, 0.39, 0.36, 0.3, 0.24,
            0.18, 0.21, 0.27, 0.33, 0.45, 0.54, 0.51, 0.45, 0.39, 0.3,
            0.27, 0.21, 0.18, 0.15, 0.21, 0.27, 0.33, 0.36, 0.3, 0.24,
        ]

        data_points = [
            ft.LineChartDataPoint(x, y)
            for x, y in zip(rms_times, rms_values)
        ]

        data_series = [
            ft.LineChartData(
                data_points=data_points,
                stroke_width=4,
                color=ft.Colors.GREY_400,
                curved=True,
            )
        ]

        chart = ft.LineChart(
            data_series=data_series,
            min_x=min(rms_times),
            max_x=max(rms_times),
            min_y=0,
            max_y=max(rms_values) * 1.1,  # small buffer above peak
            expand=True,
            tooltip_bgcolor=ft.Colors.BLUE_GREY,
            tooltip_fit_inside_horizontally=True,
            tooltip_fit_inside_vertically=True,
        )

        self.rms_box = ft.Container(
            content=chart,
            expand=True,
            height=400,
            bgcolor=ft.Colors.GREY_600,
            border_radius=10,
            padding=10
        )

        self.rms_display: ft.Column = ft.Column(
            [
                ft.Text("RMS over time"),
                self.rms_box
            ],
            expand=True,
            height=400
        )

    def _initialize_controls(self):
        self._initialize_file_selectors()
        self._initialize_searchbar()

        self._initialize_tempo_box()
        self._initialize_duration_box()
        self._initialize_chroma_box()
        self._initialize_rms_values_box()

        data_column: ft.Column = ft.Column(
            [
                ft.Row(
                    [
                        self.diration_display,
                        self.tempo_display
                    ]
                ),
                ft.Row(
                    [
                        self.chroma_display,
                        self.rms_display
                    ]
                )
            ],
            alignment=ft.MainAxisAlignment.START
        )

        self.page_view = ft.Row(
            [
                self.sidebar,
                ft.Container(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    self.searchbar,
                                    ft.Container(self.song_selector, alignment=ft.Alignment(0, 0), height=50)
                                ]
                            ),
                            ft.Container(
                                expand=3
                            ),
                            data_column,
                            ft.Container(
                                expand=1
                            )
                        ],
                        spacing=15,
                        alignment=ft.MainAxisAlignment.START
                    ),
                    padding=10,
                    expand=8
                )
            ],
            spacing=0,
            expand=True
        )

    def append_error(self, error_control: ft.Control):
        current_last_control_data = self.page_view.controls[-1].data

        if isinstance(current_last_control_data, dict) \
                and isinstance(error_control.data, dict) \
                and current_last_control_data.get("error_type") == error_control.data.get("error_type"):
            # removes the current last control if it is also an error message, this is done so that error messages
            # don't stack
            self.page_view.controls.pop()

        self.page_view.controls.append(error_control)

        self.page_view.update()

    def show(self, clear: bool = True):
        """:param clear: whether to clear the page before trying to add the page's content or not."""

        if clear:
            self.page.clean()

        self.page.view = self
        self.page.add(self.page_view)

        self.page.update()


def main(page: ft.Page):
    AudioInformation(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
