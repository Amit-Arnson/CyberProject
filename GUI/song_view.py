import flet as ft
import flet_audio as fta

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from Utils.format import format_length_from_milliseconds


class SongPlayer(ft.Container):
    def __init__(
            self,
            song_id: int,
            song_length: int,  # milliseconds
            audio_player: fta.Audio
    ):
        super().__init__()

        self.song_id = song_id
        self.song_length = song_length
        self.audio_player = audio_player

        self.song_length_string = format_length_from_milliseconds(self.song_length)

        self.length_passed: ft.Container = ft.Container(
            content=ft.Text("0:00", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
        )

        self.progress_bar = ft.Slider(
                value=0.01,
                height=5,
                expand_loose=True,
                expand=True,
                on_change_end=None,  # todo: add the on_change event to change the song location
                active_color=ft.Colors.GREY_600,
                inactive_color=ft.Colors.GREY_400,
            ),

        self.length_total = ft.Container = ft.Container(
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

        self.functional_row = ft.Row(

        )
        """this is the bottom row that contains the fast forward/backward and the play/resume/replay button"""

        self.content = ft.Column(
            [
                self.information_row,
                self.functional_row
            ]
        )

    def _update_song_length_passed(self, passed: int):
        """:param passed: the amount of time passed in milliseconds"""

        passed_string = format_length_from_milliseconds(passed)
        self.length_passed.content = ft.Text(passed_string, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),

        self.length_passed.update()


class SongView(ft.AlertDialog):
    def __init__(
            self,
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

        self.cover_art_width = 300
        self.cover_art_hight = 300
        self.b64_bytes = cover_art_b64

        self.genres = genres

        content_container = ft.Container(
            width=1000,
            height=700
        )

        self.content = content_container

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
            height=self.cover_art_hight,
        )
