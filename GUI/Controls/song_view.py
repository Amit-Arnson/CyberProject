import typing

import asyncio
import flet as ft
import flet_audio as fta

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from Utils.format import format_length_from_milliseconds

from pseudo_http_protocol import ClientMessage


class SongPlayer(ft.Container):
    def __init__(
            self,
            song_id: int,
            song_length: int,  # milliseconds
            audio_player: fta.Audio,
            load_audio: typing.Callable,
            **kwargs
    ):
        super().__init__(**kwargs)

        self.song_id = song_id
        self.song_length = song_length
        self.audio_player = audio_player
        self.load_audio = load_audio

        self.song_length_string = format_length_from_milliseconds(self.song_length)

        self.length_passed: ft.Container = ft.Container(
            content=ft.Text("0:00", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
        )

        self.progress_bar = ft.Slider(
                value=0,
                height=5,
                expand_loose=True,
                expand=True,
                on_change_end=self._move_song_to_slider,
                active_color=ft.Colors.GREY_600,
                inactive_color=ft.Colors.GREY_400,
        )

        self.length_total: ft.Container = ft.Container(
            content=ft.Text(self.song_length_string, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
        )

        self.information_row = ft.Row(
            [
                self.length_passed,
                self.progress_bar,
                self.length_total
            ]
        )
        """this is the top row that contains the progress bar and the song length/song passed"""

        self.rewind_10_seconds: ft.Container = ft.Container(
            content=ft.Icon(ft.Icons.FAST_REWIND_ROUNDED, ft.Colors.GREY_600, size=25),
            on_click=self._move_ten_seconds,
            data="backward",
        )

        self.play_button: ft.Container = ft.Container(
            ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, ft.Colors.GREY_600, size=40),
            on_click=self._play_audio,
        )

        self.skip_10_seconds: ft.Container = ft.Container(
            content=ft.Icon(ft.Icons.FAST_FORWARD_ROUNDED, ft.Colors.GREY_600, size=25),
            on_click=self._move_ten_seconds,
            data="forward",
        )

        self.functional_row = ft.Row(
            [
                self.rewind_10_seconds,
                self.play_button,
                self.skip_10_seconds
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
        """this is the bottom row that contains the fast forward/backward and the play/resume/replay button"""

        self.content = ft.Column(
            [
                self.information_row,
                self.functional_row
            ]
        )

        self.audio_player.on_position_changed = self._update_audio_progress_bar
        self.audio_player.on_state_changed = self._set_restart_button

    def _update_audio_progress_bar(self, change_event: fta.AudioPositionChangeEvent):
        current_duration_milliseconds: int = change_event.position
        max_duration: int = self.song_length

        if not max_duration:
            return

        percentage_done = current_duration_milliseconds / max_duration

        current_duration_format = format_length_from_milliseconds(current_duration_milliseconds)

        self.length_passed.content = ft.Text(current_duration_format, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600)

        # sometimes the progress percent can be a bit over the max value (by 0.000X), so we take the min value between
        # the current progress and the max, so that it never passes the max value
        self.progress_bar.value = min(self.progress_bar.max, percentage_done)

        self.update()

    def _set_restart_button(self, event: fta.AudioStateChangeEvent):
        is_finished: bool = event.state == fta.AudioState.COMPLETED

        if not is_finished:
            return

        restart_listen_icon = ft.Icon(ft.Icons.REPLAY_ROUNDED, ft.Colors.GREY_600, size=40)
        self.play_button.content = restart_listen_icon

        self.audio_player.data["playing"] = False

        self.play_button.update()

    def _move_song_to_slider(self, event):

        if not hasattr(self, "audio_player") or not self.audio_player:
            return

        song_max_length = self.song_length
        slider_percentage = float(event.data)
        new_song_position = int(song_max_length * slider_percentage)

        # we calculate the new percentage in order to remove any rounding error done when the new song position is turned
        # into an integer
        new_visual_slider_percentage = new_song_position / song_max_length

        self.progress_bar.value = new_visual_slider_percentage

        self.audio_player.seek(new_song_position)

        self.progress_bar.update()

    async def _play_audio(self, *args):
        self.load_audio()

        if not hasattr(self, "audio_player") or not self.audio_player:
            return

        if not self.audio_player.data["playing"]:
            changed_icon = ft.Icon(ft.Icons.PAUSE_ROUNDED, ft.Colors.GREY_600, size=40)
            self.audio_player.resume()
            self.audio_player.data["playing"] = True
        else:
            changed_icon = ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, ft.Colors.GREY_600, size=40)
            self.audio_player.pause()
            self.audio_player.data["playing"] = False

        self.play_button.content = changed_icon
        self.play_button.update()

    def _move_ten_seconds(self, event: ft.ControlEvent):
        move_button: ft.Container = event.control

        is_action_skip = move_button.data == "forward"

        if not hasattr(self, "audio_player") or not self.audio_player:
            return

        audio_player: fta.Audio = self.audio_player

        current_position = audio_player.get_current_position()

        if not current_position:
            return

        if is_action_skip:
            new_position = current_position + 10000
        else:
            new_position = current_position - 10000

        audio_player.seek(new_position)


class SongView(ft.AlertDialog):
    def __init__(
            self,
            transport: EncryptedTransport,
            user_cache: ClientSideUserCache,
            cover_art_b64: str,
            song_id: int,
            artist_name: str,
            album_name: str,
            song_name: str,
            song_length: int,  # milliseconds
            genres: list[str],
            **kwargs
    ):
        super().__init__(**kwargs)
        self.shape = ft.RoundedRectangleBorder(radius=10)

        self.transport = transport
        self.user_cache = user_cache

        self.audio_player = fta.Audio(
            src_base64="0",
            data={"playing": False},
            autoplay=True,
            release_mode=fta.audio.ReleaseMode.STOP
        )

        self.cover_art_width = 300
        self.cover_art_height = 300
        self.b64_bytes = cover_art_b64

        self.song_id = song_id
        self.song_length = song_length
        self.song_name = song_name
        self.artist_name = artist_name

        self.genres = genres

        self.graphical_information: ft.Row = ft.Row(
            [
                self._create_cover_art(),
                ft.Column(
                    [
                        ft.Text(song_name, size=35, weight=ft.FontWeight.W_500),
                        ft.Text(artist_name, size=30, weight=ft.FontWeight.W_200),
                        ft.Row([*self._create_genre_list()])
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=0
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        """displays the purely graphical information, such as cover art and song/artist name"""

        self.functional_information: ft.Row = ft.Row(
            [
                self.audio_player,
                SongPlayer(
                    song_id=self.song_id,
                    song_length=self.song_length,
                    audio_player=self.audio_player,
                    load_audio=self._request_song_chunks,
                    height=100,
                    expand=True,
                    expand_loose=True,
                )
            ],
        )
        """displays the functional information, which is the GUI that can be interacted with (such as the play bar)"""

        self.display_column: ft.Column = ft.Column(
            [
                self.graphical_information,
                self.functional_information
            ],
            width=1000,
            height=700,
            spacing=50,
        )

        self.content = self.display_column
        self.on_dismiss = self._on_dismiss

    # currently buffering does not work as once you update the page, the audio restarts to the start.
    # todo: see if i should create a temp file and use src instead (not sure if it will work or not)
    # todo: see if i should create a proxy http server to send the bytes and use src instead of b64. this will 100% work but will require a lot of work
    async def stream_audio_chunks(self, file_id: str, song_id: int, b64_chunk: str, is_last_chunk: bool = False):
        if not song_id == self.song_id:
            return

        # if the src == "0" it means the song wasn't loaded yet
        if self.audio_player.src_base64 == "0":
            self.audio_player.src_base64 = b64_chunk
        else:
            self.audio_player.src_base64 += b64_chunk

        self.audio_player.update()

    def _on_dismiss(self, *args):
        self.audio_player.pause()
        self.audio_player.release()

        self.audio_player.update()

        if hasattr(self.page, "view"):
            self.page.view.is_viewing_song = False
            self.page.view.song_view_popup = None

    def _create_genre_list(self) -> list[ft.Container]:
        return [
            ft.Container(
                content=ft.Text(genre),
                padding=10,
                bgcolor=ft.Colors.GREY,
                border_radius=10
            )
            for genre in self.genres
        ]

    def _create_cover_art(self) -> ft.Image:
        return ft.Image(
            src_base64=self.b64_bytes,
            fit=ft.ImageFit.FILL,
            # images below a certain resolution did not fully cover the container when using ImageFit, so i set
            # a manual width and height that will be equal to what the gridview allows and thus will always fit
            width=self.cover_art_width,
            height=self.cover_art_height,
        )

    def _request_song_chunks(self):
        # if the src == "0" it means the song wasn't loaded yet
        if self.audio_player.src_base64 != "0":
            return

        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="GET",
                endpoint="song/download/audio",
                payload={
                    "song_id": self.song_id
                }
            ).encode()
        )
