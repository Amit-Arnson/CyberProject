import base64
import hashlib
import time
import datetime
import typing

import aiofiles
from pathlib import Path
import os

import asyncio
import flet as ft
import flet_audio as fta

from GUI.Controls.subwindow import SubWindow

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

        self.length_passed.content = ft.Text(current_duration_format, weight=ft.FontWeight.BOLD,
                                             color=ft.Colors.GREY_600)

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


class SheetView(ft.Container):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sheet_images: list[tuple[str, ft.Container]] = []
        """list[tuple[file id, sheet image]]]"""

        self.expand = True

        self.sheet_row: ft.Row = ft.Row(
            wrap=True,
            tight=True,
        )

        no_sheets_found = ft.Container(
            ft.Text("No Sheets Found"),
            expand_loose=True,
            height=300,
            alignment=ft.Alignment(0, 0)
        )
        self.has_started_loading = False

        self.content = ft.Container(
            content=no_sheets_found
        )

    def _upsize_image(self, event):
        self.sheet_row.controls.append(
            ft.AlertDialog(
                open=True,
                content=ft.InteractiveViewer(
                    ft.Container(
                        width=450,
                        height=600,
                        content=event.control.content,
                        border_radius=10,
                        padding=10
                    ),
                    min_scale=0.1,
                    max_scale=15,
                ),
                bgcolor=ft.Colors.with_opacity(1, ft.Colors.WHITE)
            )
        )

        self.update()

    def get_sheet_container(self, file_id: str) -> ft.Container | None:
        for saved_file_id, image in self.sheet_images:
            if saved_file_id == file_id:
                return image

        return None

    def add_chunk(self, file_id: str, song_id: int, b64_chunk: str, is_last_chunk: bool = False):
        if not self.has_started_loading:
            self.content = ft.Container(
                self.sheet_row,
                alignment=ft.Alignment(-1, -1),
                padding=ft.Padding(
                    top=15,
                    bottom=5,
                    right=5,
                    left=5
                )
            )

            self.has_started_loading = True

        image_container = self.get_sheet_container(file_id)

        if not image_container:
            image_container = ft.Container(
                width=150,
                height=200,
                content=ft.Image(
                    src_base64=b64_chunk,
                    fit=ft.ImageFit.FILL,
                    width=150,
                    height=200,
                    border_radius=10
                ),
                on_click=self._upsize_image,
                border_radius=10,
                bgcolor=ft.Colors.GREY_600,
                border=ft.border.all(width=2, color=ft.Colors.GREY_400)
            )

            self.sheet_images.append(
                (file_id, image_container)
            )

            self.sheet_row.controls.append(image_container)
        else:
            image: ft.Image = image_container.content
            image.src_base64 += b64_chunk

        self.update()


class CommentView(ft.Container):
    def __init__(self, transport: EncryptedTransport, user_cache: ClientSideUserCache, song_id: int, **kwargs):
        super().__init__(**kwargs)

        self.transport = transport
        self.user_cache = user_cache
        self.song_id = song_id

        self.comments: list[dict[str, int | str]] = []
        """
        list[
            {
                "comment_id": int,
                "text": str,
                "uploaded_at": int,
                "uploaded_by": str
            }
        ]
        """

        self.comments_exclude_ids: list[int] = []

        self.temporary_comments: list[ft.Container] = []
        """these are for comments that we add during the open view, and need to be removed when closing and reopening"""

        self.expand = True

        self.comment_textbox: ft.TextField = ft.TextField(
            on_submit=self._upload_comment,
            max_length=2000,
            multiline=True,
            shift_enter=True,
        )

        self.comment_list: ft.ListView = ft.ListView(
            spacing=5,
            padding=5,
            expand=True,
        )

        self.username_colors_cache: dict[str, str] = {}

        self.loaded_ai_comment: bool = False

        self.content = ft.Container(
            content=ft.Column(
                [
                    self.comment_textbox,
                    self.comment_list
                ]
            ),
            padding=ft.Padding(
                top=15,
                bottom=5,
                right=5,
                left=5
            )
        )

    @staticmethod
    def _convert_timestamp(timestamp):
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        time_string = f"{dt_object.hour}:{dt_object.minute if len(str(dt_object.minute)) > 1 else '0' + str(dt_object.minute)}"
        date_string = f"{dt_object.day}/{dt_object.month}/{dt_object.year}"

        today = datetime.date.today()

        if today == dt_object.date():
            dt_string = f"Today at {time_string}"
        else:
            dt_string = f"{date_string} {time_string}"

        return dt_string

    def _string_to_hex_color(self, string: str) -> str:
        if string in self.username_colors_cache:
            return self.username_colors_cache[string]

        hash_bytes = hashlib.sha256(string.encode()).digest()
        r, g, b = hash_bytes[0], hash_bytes[1], hash_bytes[2]

        # force the color to be on the lighter side by blending toward white (255)
        # we need to do this because making a system that switches the profile image letter's color from white to black
        # is much harder than just ensuring that the background color is light.
        def lighten(value, min_brightness=180):
            return int(value * 0.5 + 255 * 0.5) if value < min_brightness else value

        r, g, b = lighten(r), lighten(g), lighten(b)
        color = f'#{r:02x}{g:02x}{b:02x}'

        self.username_colors_cache[string] = color
        return color

    def _upload_comment(self, event: ft.ControlEvent):
        comment_text = self.comment_textbox.value

        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="POST",
                endpoint="song/comments/upload",
                payload={
                    "text": comment_text,
                    "song_id": self.song_id
                }
            ).encode()
        )

        self.comment_textbox.value = None

        comment_content_view = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(self.user_cache.display_name[0]),
                        bgcolor=self._string_to_hex_color(self.user_cache.username),
                        border_radius=360,
                        alignment=ft.Alignment(0, 0),
                        width=40,
                        height=40
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(self.user_cache.display_name),
                                    ft.Text(self._convert_timestamp(int(time.time())), color=ft.Colors.GREY_500,
                                            size=10)
                                ]
                            ),
                            ft.Text(comment_text)
                        ],
                        expand=True,
                        expand_loose=True,
                    )
                ],
                vertical_alignment=ft.CrossAxisAlignment.START
            ),
            width=200,
            bgcolor=ft.Colors.GREY_200,
            border_radius=10,
            padding=10,
        )
        self.temporary_comments.append(comment_content_view)

        if self.comment_list.controls[-1].data == 999:
            self.comment_list.controls.pop(-1)

        self.comment_list.controls.append(comment_content_view)

        self.update()

    def close(self):
        for comment in self.temporary_comments:
            try:
                self.comment_list.controls.remove(comment)
            except ValueError:
                pass

    def add_comments(self, comments: list[dict], ai_summary: str):
        if not self.loaded_ai_comment:
            ai_summary_view = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=ft.Colors.GREY_800),
                                ft.Text("AI summary", size=15, color=ft.Colors.GREY_800, weight=ft.FontWeight.W_500)
                            ]
                        ),
                        ft.Text(ai_summary)
                    ]
                ),
                border_radius=10,
                bgcolor=ft.Colors.BLUE_400,
                padding=10
            )

            self.comment_list.controls.append(ai_summary_view)

            self.loaded_ai_comment = True

        if len(comments) == 0 and len(self.comments) == 0:
            no_comments_found = ft.Container(
                ft.Text("No Comments Found"),
                expand_loose=True,
                height=100,
                alignment=ft.Alignment(0, 0),
                data=999
            )

            self.comment_list.controls.append(no_comments_found)

        for comment in comments:
            self.comments.append(comment)

            comment_id: int = comment["comment_id"]
            self.comments_exclude_ids.append(comment_id)

            content: str = comment["text"]
            uploaded_by: str = comment["uploaded_by"]
            uploaded_by_display_name: str = comment["uploaded_by_display"]
            uploaded_at: int = comment["uploaded_at"]

            comment_content_view = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(uploaded_by_display_name[0]),
                            bgcolor=self._string_to_hex_color(uploaded_by),
                            border_radius=360,
                            alignment=ft.Alignment(0, 0),
                            width=40,
                            height=40
                        ),
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(uploaded_by_display_name),
                                        ft.Text(self._convert_timestamp(uploaded_at), color=ft.Colors.GREY_500, size=10)
                                    ]
                                ),
                                ft.Text(content)
                            ],
                            expand=True,
                            expand_loose=True,
                        )
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START
                ),
                width=200,
                bgcolor=ft.Colors.GREY_200,
                border_radius=10,
                padding=10,
            )

            self.comment_list.controls.append(comment_content_view)

        self.comment_list.update()

    def request_comments(self):
        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="GET",
                endpoint="song/comments",
                payload={
                    "exclude": self.comments_exclude_ids,
                    "song_id": self.song_id
                }
            ).encode()
        )


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
                        ft.Column(
                            [
                                ft.Text(song_name, size=35, weight=ft.FontWeight.W_500),
                                ft.Text(artist_name, size=30, weight=ft.FontWeight.W_200),
                            ],
                            spacing=0,
                        ),
                        ft.Row([*self._create_genre_list()], wrap=True),
                        ft.Row(
                            [
                                ft.Container(
                                    ft.Icon(ft.Icons.STAR_ROUNDED, color=ft.Colors.BLACK),
                                    on_click=self._toggle_favorite
                                ),
                                ft.Container(
                                    ft.Icon(ft.Icons.DOWNLOAD, color=ft.Colors.BLACK),
                                    on_click=self._locally_download_audio
                                ),
                                ft.Container(
                                    content=ft.Icon(ft.Icons.COMMENT_ROUNDED, color=ft.Colors.BLACK),
                                    on_click=self._open_comment_view_popup
                                ),
                                ft.Container(
                                    content=ft.Icon(ft.Icons.SIM_CARD_DOWNLOAD_ROUNDED, color=ft.Colors.BLACK),
                                    on_click=self._open_sheet_music_popup
                                )
                            ]
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=10
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

        self.view = ft.Stack(
            [
                self.display_column
            ],
            width=1000,
            height=700,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

        self.is_waiting_for_local_download = False
        self.downloading_audio_cover = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("downloading audio", color=ft.Colors.WHITE),
                        ft.ProgressRing()
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                expand=True,
                expand_loose=True,
                alignment=ft.Alignment(0, 0),
            ),
            modal=True,
            open=True,
            bgcolor=ft.Colors.with_opacity(0, ft.Colors.BLACK)
        )

        self.is_viewing_comments = False
        self.is_viewing_sheets = False

        self.sheet_music_view_control = SheetView()
        self.has_loaded_sheets = False

        self.comment_view = CommentView(
            transport=self.transport,
            user_cache=self.user_cache,
            song_id=self.song_id
        )

        self.content = self.view
        self.on_dismiss = self._on_dismiss

    def _open_sheet_music_popup(self, event):
        if self.is_viewing_sheets:
            return

        self.is_viewing_sheets = True

        dialog = SubWindow(
            width=500,
            height=300,
            on_close=self._close_sheet_music_popup
        )

        dialog.set_content(self.sheet_music_view_control)

        self.view.controls.append(dialog)

        self.update()

        self._request_song_sheet_chunks()

    def _open_comment_view_popup(self, event):
        if self.is_viewing_comments:
            return

        self.is_viewing_comments = True

        dialog = SubWindow(
            width=300,
            height=300,
            on_close=self._close_comment_popup
        )

        dialog.set_content(self.comment_view)

        self.view.controls.append(dialog)

        self.update()

        self.comment_view.request_comments()

    def _close_sheet_music_popup(self):
        self.is_viewing_sheets = False

    def _close_comment_popup(self):
        self.is_viewing_comments = False
        self.comment_view.close()

    async def stream_audio_chunks(self, file_id: str, song_id: int, b64_chunk: str, is_last_chunk: bool = False):
        if not song_id == self.song_id:
            return

        self.audio_player.pause()

        # if the src == "0" it means the song wasn't loaded yet
        if self.audio_player.src_base64 == "0":
            self.audio_player.src_base64 = b64_chunk
        else:
            self.audio_player.src_base64 += b64_chunk

        if not self.is_waiting_for_local_download:
            self.audio_player.update()

        if is_last_chunk and self.is_waiting_for_local_download:
            self.view.controls.remove(self.downloading_audio_cover)
            self.view.update()

            await self._download_audio()

    async def stream_sheet_chunks(self, file_id: str, song_id: int, b64_chunk: str, is_last_chunk: bool = False):
        self.sheet_music_view_control.add_chunk(file_id, song_id, b64_chunk, is_last_chunk)

    async def add_comments(self, comments: list[dict], ai_summary: str):
        self.comment_view.add_comments(comments, ai_summary=ai_summary)

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

    async def _download_audio(self):
        audio_file_bytes: bytes = base64.b64decode(self.audio_player.src_base64)

        # Construct filename
        file_name = f"{self.song_name} - {self.artist_name}.aac"

        # Get user's Downloads folder (cross-platform)
        downloads_folder = str(Path.home() / "Downloads")

        # Combine full path
        file_path = os.path.join(downloads_folder, file_name)

        # Save to Downloads
        async with aiofiles.open(file_path, "wb") as file:
            await file.write(audio_file_bytes)

        await asyncio.create_subprocess_exec("explorer", "/select,", str(file_path))

        self.is_waiting_for_local_download = False

        self.view.controls.append(
            ft.AlertDialog(
                content=ft.Container(ft.Text("Successfully downloaded file!")),
                open=True
            )
        )

        self.update()

    async def _locally_download_audio(self, *args):
        self.is_waiting_for_local_download = True

        if self.audio_player.src_base64 == "0":
            self.view.controls.append(self.downloading_audio_cover)
            self.update()

            self._request_song_chunks()
        else:
            await self._download_audio()

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

    def _toggle_favorite(self, *args):
        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="POST",
                endpoint="song/favorite/toggle",
                payload={
                    "song_id": self.song_id
                }
            ).encode()
        )

    def _request_song_sheet_chunks(self):
        if self.has_loaded_sheets:
            return

        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="GET",
                endpoint="song/download/sheets",
                payload={
                    "song_id": self.song_id
                }
            ).encode()
        )

        self.has_loaded_sheets = True
