import base64
import logging

import aiofiles
import asyncio

import flet as ft
import flet_audio as fta

from encryptions import EncryptedTransport

from GUI.Controls.navigation_sidebar import NavigationSidebar
from GUI.Controls.tag_input import TagInput

from Caches.user_cache import ClientSideUserCache

from Utils.chunk import send_chunk
from Utils.format import format_length_from_milliseconds, format_file_size


# This section was moved to a class due to being hard to read when inside of a function
class ImageRemoveHover(ft.Stack):
    def __init__(self, image: ft.Image, image_name: str, width: int, height: int):
        super().__init__()

        self.image = image
        self.image_name = image_name
        self.width = width
        self.height = height

        # Define controls using helper methods for better organization
        self.controls = [
            self._create_image_container(),
            self._create_gradient_overlay(),
            self._create_close_icon_overlay(),
            self._create_text_overlay(),
        ]

    def _create_image_container(self) -> ft.Container:
        """Creates the container for the image."""
        return ft.Container(
            content=self.image,
            width=self.width,
            height=self.height,
        )

    def _create_gradient_overlay(self) -> ft.Container:
        """Creates the gradient overlay container."""
        return ft.Container(
            gradient=ft.LinearGradient(
                colors=[
                    ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                ],
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
            ),
            width=self.width,
            height=self.height,
            padding=5,
        )

    def _create_close_icon_overlay(self) -> ft.Container:
        """Creates the close icon overlay container."""
        return ft.Container(
            content=ft.Container(
                content=ft.Icon(
                    ft.Icons.CLOSE,
                    color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                ),
                width=self.width / 5,
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.GREY),
                border_radius=180,
                expand_loose=True,
                alignment=ft.Alignment(0, 0),
            ),
            padding=5,
            height=40,
            top=0,
            left=0,
        )

    def _create_text_overlay(self) -> ft.Container:
        """Creates the text overlay container."""
        return ft.Container(
            content=ft.Container(
                content=ft.Text(
                    self.image_name,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                padding=5,
                width=self.width - 10,
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.GREY),
                border_radius=10,
                expand_loose=True,
                alignment=ft.Alignment(0, 0),
            ),
            padding=5,
            height=40,
            bottom=0,
        )


class UploadCoverArtDefault(ft.Stack):
    def __init__(self, height: int = 150, width: int = 150):
        super().__init__()

        self.height = height
        self.width = width

        # Default size values for containers
        self.default_size_values: dict[str, int] = {
            "width": 25,
            "height": 25,
        }

        # Default border styling
        self.default_border_value = ft.BorderSide(
            color=ft.Colors.GREY_700, width=2
        )

        # Define controls for upload cover art
        self.controls = [
            self._create_main_text_container(),
            self._create_corner_container(bottom=0, right=0, add_sides=["right", "bottom"]),
            self._create_corner_container(bottom=0, left=0, add_sides=["left", "bottom"]),
            self._create_corner_container(top=0, right=0, add_sides=["right", "top"]),
            self._create_corner_container(top=0, left=0, add_sides=["left", "top"]),
        ]

    def _create_main_text_container(self) -> ft.Container:
        """Creates the main text container."""
        return ft.Container(
            content=ft.Text(
                spans=[
                    ft.TextSpan("ADD\n"),
                    ft.TextSpan("COVER"),
                ],
                text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREY_500,
            ),
            height=self.height,
            width=self.width,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_500),
            alignment=ft.Alignment(0, 0),
        )

    def _create_corner_container(self, **kwargs) -> ft.Container:
        """
        Creates a corner container with specified positioning and border sides.

        :param kwargs: Positioning arguments (e.g., top, bottom, left, right).
        :param add_sides: List of sides for which borders are added.
        """
        add_sides = kwargs.pop("add_sides", [])
        border_kwargs = {
            side: self.default_border_value for side in add_sides
        }

        return ft.Container(
            **self.default_size_values,
            border=ft.Border(**border_kwargs),
            **kwargs,
        )


class UploadPage:
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

        # this holds the session token (which is the authentication)
        self.user_cache: ClientSideUserCache | None = None
        if hasattr(page, "user_cache"):
            self.user_cache: ClientSideUserCache = page.user_cache

        self.sheet_image_container_id = 0

        # this is the ID-path dict for image sheet paths, so you need to use the .values() to get the paths themselves
        self.sheet_file_paths: dict[int, str] = {}
        self.selected_song_path: str = ""
        self.selected_cover_art_path: str = ""

        self.upload_cover_art_default_content: ft.Container = ft.Container(
            UploadCoverArtDefault(),
            height=150,
            width=150,
            on_click=self._select_cover_art_file
        )

        self.sidebar = NavigationSidebar(page=page)
        # override the on_click method so that clicking on the button does not reset the information already input
        self.sidebar.goto_upload_song.on_click = None

        # the sidebar is set to 2 and the right side of the page is set to 10. this means the sidebar takes 20% of the
        # available screen
        self.sidebar.expand = 2

        # we define 3 different file pickers so that we can point the on_result to different functions in order to make
        # sorting between images (between sheet and cover) and audio files easier
        self.sound_file_picker = ft.FilePicker()
        self.sound_file_picker.on_result = self._on_finish_audio_select

        self.image_file_picker = ft.FilePicker()
        self.image_file_picker.on_result = self._on_finish_image_select

        self.cover_art_file_picker = ft.FilePicker()
        self.cover_art_file_picker.on_result = self._on_finish_cover_art_select

        # size of the files in bytes
        self.selected_audio_size = 0
        self.selected_images_size = 0
        self.selected_cover_art_size = 0

        self.MEGABYTE = 1024 * 1024
        self.MAX_AUDIO_SIZE = 25 * self.MEGABYTE
        self.MAX_IMAGES_SIZE = 10 * self.MEGABYTE
        self.MAX_COVER_ART_SIZE = 2 * self.MEGABYTE

        # add the file picker control to the page
        self.page.overlay.append(self.sound_file_picker)
        self.page.overlay.append(self.image_file_picker)
        self.page.overlay.append(self.cover_art_file_picker)

        self.blocking_overlay = ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            content=ft.Text("Uploading", size=35, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            alignment=ft.Alignment(0, 0)
        )

        self._initialize_controls()

    # todo: see if this function is still needed
    def _initialize_sidebar_top(self):
        pass

    async def _upload_all_files(self, *args):
        session_token: str = self.user_cache.session_token
        print(f"session token: {session_token}")

        image_paths: list[str] = list(self.sheet_file_paths.values())
        audio_path: str = self.selected_song_path
        cover_art_path: str = self.selected_cover_art_path

        tags = self.selected_genres_textbox.get_values()
        artist_name = self.song_artist_textbox.value
        album_name = self.song_album_textbox.value
        song_name = self.song_name_textbox.value

        # todo: create the GUI error for these
        if not audio_path:
            raise "No song selected"
        # we don't check for "less than 100" on the names, or "less than 5" on the tags because the GUI already blocks
        # anything over 100, so it would be pointless to check it.
        # (if a malicious user uses a modified client, checking it here in addition to the GUI won't add any level of
        # security, because the sever also checks it when it reaches the server)
        if not artist_name or not album_name or not song_name or not tags:
            raise "You must add a song name, album name, artist name and at least 1 tag"

        self._add_blocking_overlay()

        # uses the page's async event loop to create a task
        self.send_chunks_task = self.page.loop.create_task(
            send_chunk(
                transport=self.transport,
                session_token=session_token,
                tags=tags,
                artist_name=artist_name,
                album_name=album_name,
                song_name=song_name,
                song_path=audio_path,
                covert_art_path=cover_art_path,
                image_path_list=image_paths
            )
        )

        try:
            await self.send_chunks_task
        except asyncio.CancelledError:
            self.remove_blocking_overlay()
        except Exception as e:
            logging.error(e)
            self.remove_blocking_overlay()
        finally:
            self._clear_page()

    def _add_blocking_overlay(self):
        self.page.overlay.append(
            self.blocking_overlay
        )

        self.page.update()

    def remove_blocking_overlay(self):
        if self.page.overlay[-1] == self.blocking_overlay:
            self.page.overlay.pop()

            self.page.update()

    # ------------------------------------------------------------------------------------------------------------------

    def _select_sound_files(self, e: ft.ControlEvent):
        self.sound_file_picker.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.AUDIO
        )

    def _select_image_files(self, e: ft.ControlEvent):
        self.image_file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.IMAGE
        )

    def _select_cover_art_file(self, e: ft.ControlEvent):
        self.cover_art_file_picker.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.IMAGE
        )

    # -----------------------------------------------------------------------------------------------------------------

    def _reset_audio_player_info(self, update: bool = True):
        """:param update: whether to automatically update the GUI to display the cleared state"""

        song_player_info: ft.Container = self.song_selector_info_column.controls[1]
        song_player_info_row: ft.Row = song_player_info.content

        song_player_info_row.controls = [
            ft.Container(
                ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, ft.Colors.GREY_600, size=40),
                on_click=self._play_audio,
            ),
            ft.Text(spans=[
                ft.TextSpan("0:00"), ft.TextSpan("/"), ft.TextSpan("0:00")
            ], weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
            ft.Container(
                content=ft.Icon(
                    ft.Icons.FAST_REWIND_ROUNDED, ft.Colors.GREY_600, size=25
                ),
                on_click=self._move_ten_seconds,
                data="backward",
            ),
            ft.Slider(
                value=0.01,
                height=5,
                expand_loose=True,
                expand=True,
                on_change_end=self._move_song_to_slider,
                active_color=ft.Colors.GREY_600,
                inactive_color=ft.Colors.GREY_400,
            ),
            ft.Container(
                content=ft.Icon(
                    ft.Icons.FAST_FORWARD_ROUNDED, ft.Colors.GREY_600, size=25
                ),
                on_click=self._move_ten_seconds,
                data="forward",
            )
        ]

        if update:
            song_player_info_row.update()

    def _update_audio_player_info(self, audio_duration_changed: fta.AudioDurationChangeEvent):
        song_length_milliseconds: int = audio_duration_changed.duration

        song_player_info: ft.Container = self.song_selector_info_column.controls[1]
        song_player_info_row: ft.Row = song_player_info.content
        # [0] -> play button
        # [1] -> duration
        # [2] -> fast-backward
        # [3] -> progress bar
        # [4] -> fast-forward

        duration = format_length_from_milliseconds(song_length_milliseconds)
        new_duration_text = ft.Text(
            spans=[
                ft.TextSpan("0:00"),
                ft.TextSpan("/"),
                ft.TextSpan(f"{duration}")
            ], weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600
        )

        song_player_info_row.controls[1] = new_duration_text

        song_player_info_row.update()

        # so that it doesn't reset the duration counter every time it thinks that the song's duration got updated (such
        # as when pausing and resuming)
        self.audio_player.on_duration_changed = None

    def _play_audio(self, event: ft.ControlEvent):
        play_button: ft.Container = event.control

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

        play_button.content = changed_icon
        play_button.update()

    def _update_audio_progress_bar(self, change_event: fta.AudioPositionChangeEvent):
        current_duration_milliseconds: int = change_event.position
        max_duration: int = self.audio_player.get_duration()

        # if there is no max duration, that means the user just removed the audio from being selected
        if not max_duration:
            return

        percentage_done = current_duration_milliseconds / max_duration

        song_player_info: ft.Container = self.song_selector_info_column.controls[1]
        song_player_info_row: ft.Row = song_player_info.content
        # [0] -> play button
        # [1] -> duration
        # [2] -> fast-backward
        # [3] -> progress bar
        # [4] -> fast-forward

        max_duration_format = format_length_from_milliseconds(max_duration)
        current_duration_format = format_length_from_milliseconds(current_duration_milliseconds)
        new_duration_text = ft.Text(
            spans=[
                ft.TextSpan(f"{current_duration_format}"),
                ft.TextSpan("/"),
                ft.TextSpan(f"{max_duration_format}")
            ], weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600
        )

        song_player_info_row.controls[1] = new_duration_text

        progress_bar: ft.Slider = song_player_info_row.controls[3]

        # sometimes the progress percent can be a bit over the max value (by 0.000X), so we take the min value between
        # the current progress and the max, so that it never passes the max value
        progress_bar.value = min(progress_bar.max, percentage_done)

        song_player_info_row.update()

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

    def _move_song_to_slider(self, event):

        if not hasattr(self, "audio_player") or not self.audio_player:
            return

        song_max_length = self.audio_player.get_duration()
        slider_percentage = float(event.data)
        new_song_position = int(song_max_length * slider_percentage)

        # we calculate the new percentage in order to remove any rounding error done when the new song position is turned
        # into an integer
        new_visual_slider_percentage = new_song_position / song_max_length

        song_player_info: ft.Container = self.song_selector_info_column.controls[1]
        song_player_info_row: ft.Row = song_player_info.content

        progress_bar: ft.Slider = song_player_info_row.controls[3]
        progress_bar.value = new_visual_slider_percentage

        self.audio_player.seek(new_song_position)

        progress_bar.update()

    def _set_restart_button(self, event: fta.AudioStateChangeEvent):
        is_finished: bool = event.state == fta.AudioState.COMPLETED

        if not is_finished:
            return

        song_player_info: ft.Container = self.song_selector_info_column.controls[1]
        song_player_info_row: ft.Row = song_player_info.content
        # [0] -> play button

        play_button: ft.Container = song_player_info_row.controls[0]

        restart_listen_icon = ft.Icon(ft.Icons.REPLAY_ROUNDED, ft.Colors.GREY_600, size=40)
        play_button.content = restart_listen_icon

        self.audio_player.data["playing"] = False

        play_button.update()

    async def _buffer_audio(self, path: str):
        self.audio_player = fta.Audio(
            src=path,
            on_duration_changed=self._update_audio_player_info,
            on_position_changed=self._update_audio_progress_bar,
            on_state_changed=self._set_restart_button,
            data={"playing": False}
        )

        self.page_view.controls.append(self.audio_player)
        self.page_view.update()

        self.audio_player.play()

    def _remove_selected_song(self, *args, update: bool = True):
        """:param update: whether to automatically update the GUI to display the cleared state"""

        self.song_selector_info_column.controls[0] = self.song_selector

        # removes the selected song path from the saved paths
        self.selected_song_path = ""
        self.selected_audio_size = 0

        for control in self.page_view.controls.copy():
            if isinstance(control, fta.Audio):
                control.release()
                self.page_view.controls.remove(control)
                self._reset_audio_player_info()

        if update:
            self.song_selector_info_column.update()

    async def _on_finish_audio_select(self, e: ft.FilePickerResultEvent):
        selected_files = e.files

        if not selected_files:
            return

        audio_file = selected_files[0]
        file_path: str = audio_file.path

        self.selected_song_path = file_path
        audio_size = audio_file.size

        if audio_size > self.MAX_AUDIO_SIZE:
            self._show_file_too_big_error(self.MAX_AUDIO_SIZE)

            return

        self.selected_audio_size = audio_size

        audio_file_details: ft.Container = ft.Container(
            padding=10,
            expand=True,
            content=ft.Row(
                expand=True,
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.RED, size=25),
                        on_click=self._remove_selected_song
                    ),
                    ft.Text(f"{audio_file.name} | {format_file_size(audio_file.size)}", size=25),
                ]
            ),
            alignment=ft.Alignment(-1, 0)
        )

        self.song_selector_info_column.controls[0] = audio_file_details
        await self._buffer_audio(path=file_path)

        self.song_selector_info_column.update()

    # ---- image (sheet music) selection related stuff ----

    def _on_finish_image_select(self, e: ft.FilePickerResultEvent):
        selected_files = e.files

        if not selected_files:
            return

        total_selected_size = sum((file.size for file in selected_files))

        if self.selected_images_size + total_selected_size > self.MAX_IMAGES_SIZE:
            # todo: show an error in the GUI (in the used/max GUI, not popup)
            self._show_file_too_big_error(self.MAX_IMAGES_SIZE)

            return

        # only continue actually adding the images if the new total size is in the allowed limit
        self.selected_images_size += total_selected_size
        self._update_sheet_selector_max_size_text()

        self._add_music_sheets_to_row(selected_files)

    def _remove_sheet_image(self, event: ft.ControlEvent):
        image_container = event.control

        image_unique_id: int = image_container.data["id"]
        image_size: int = image_container.data["size"]

        # removes the container from the sheet row
        self.sheet_selector_row.controls.remove(image_container)

        # removes the path from the dictionary, along with its ID key
        del self.sheet_file_paths[image_unique_id]

        # reduce the selected images sizes
        self.selected_images_size -= image_size
        self._update_sheet_selector_max_size_text()

        self.sheet_selector_row.update()

    def _clear_sheet_images(self, update: bool = True):
        """:param update: whether to automatically update the GUI to display the cleared state"""

        sheet_selector = self.sheet_selector_row.controls.pop()

        self.sheet_selector_row.controls.clear()

        self.sheet_selector_row.controls.append(sheet_selector)

        # removes everything from the paths dictionary
        self.sheet_file_paths.clear()
        self.selected_images_size = 0

        self._update_sheet_selector_max_size_text()

        if update:
            self.sheet_selector_row.update()

    @staticmethod
    def _hover_sheet_image(event: ft.ControlEvent):
        image_container = event.control

        if event.data == "true":
            image: ft.Image = image_container.content

            image_name: str = image.data

            image_remove_overlay: ft.Stack = ImageRemoveHover(
                image=image,
                image_name=image_name,
                width=image_container.width,
                height=image_container.height
            )

            image_container.content = image_remove_overlay
        else:
            image_remove_overlay: ft.Stack = image_container.content

            image: ft.Image = image_remove_overlay.controls[0].content

            image_container.content = image

        image_container.update()

    def _add_music_sheets_to_row(self, selected_files: list[ft.core.file_picker.FilePickerFile]):
        image_containers: list[ft.Container] = []

        for file in selected_files:
            current_id = self.sheet_image_container_id
            path = file.path
            name = file.name
            size = file.size

            image_container = ft.Container(
                width=150,
                height=190,
                content=ft.Image(
                    src=path,
                    fit=ft.ImageFit.FILL,
                    data=name
                ),
                border_radius=3,
                data={
                    "id": current_id,
                    "size": size
                },
                on_click=self._remove_sheet_image,
                on_hover=self._hover_sheet_image,
            )

            # to be able to easily remove it later (when clicking on the image container), i made the saved paths into
            # a dictionary with a unique ID (since the ID number increments every time, it will never be the same number)
            self.sheet_file_paths[current_id] = path

            self.sheet_image_container_id += 1

            image_containers.append(image_container)

        # i pop the current last item (which will always be the file selector), then append it to the end.
        # this is done so that you dont need to scroll in order to get to the file selector
        sheet_selector: ft.Container = self.sheet_selector_row.controls.pop()

        image_containers.append(sheet_selector)

        self.sheet_selector_row.controls.extend(image_containers)

        self.sheet_selector_row.update()

        # scrolls to end (where the sheet_selector is)
        self.sheet_selector_row.scroll_to(offset=-1, duration=1000, curve=ft.AnimationCurve.EASE_IN_OUT)

    # -------------------------------------------------------------------------------------------------------------
    # image (cover art) selection

    def _remove_cover_art_selection(self, *args, update: bool = True):
        """:param update: whether to automatically update the GUI to display the cleared state"""

        self.selected_cover_art_path = ""
        self.selected_cover_art_size = 0

        self.song_selector_row.controls[0] = self.upload_cover_art_default_content

        if update:
            self.song_selector_row.update()

    def _on_finish_cover_art_select(self, e: ft.FilePickerResultEvent):
        selected_files = e.files

        if not selected_files:
            return

        cover_art_file = selected_files[0]
        file_path: str = cover_art_file.path

        self.selected_cover_art_path = file_path
        cover_art_size = cover_art_file.size

        if cover_art_size > self.MAX_COVER_ART_SIZE:
            self._show_file_too_big_error(self.MAX_COVER_ART_SIZE)

            return

        self.selected_cover_art_size = cover_art_size

        self.song_selector_row.controls[0] = ft.Container(
            content=ft.Image(
                src=file_path,
                fit=ft.ImageFit.FILL
            ),
            height=self.upload_cover_art_default_content.height,
            width=self.upload_cover_art_default_content.width,
            on_click=self._remove_cover_art_selection
        )

        self.song_selector_row.update()

    # ------------------------------------------------------------------------------------------------------------------

    def _clear_page(self, *args):
        self._clear_sheet_images(update=False)
        self._reset_audio_player_info(update=False)
        self._remove_cover_art_selection(update=False)
        self._remove_selected_song(update=False)
        self._clear_text_boxes(update=False)

        self._update_sheet_selector_max_size_text(update=False)

        self.page_view.update()

    def _initialize_file_selectors(self):
        self.song_selector = ft.Container(
            content=ft.Icon(ft.Icons.UPLOAD_ROUNDED, color=ft.Colors.GREY_800),
            on_click=self._select_sound_files,
            expand=True,
            expand_loose=True,
            height=150,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=3,
            alignment=ft.Alignment(0, 0)
        )

        self.song_selector_info_column: ft.Column = ft.Column(
            [
                self.song_selector,
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, ft.Colors.GREY_600, size=40),
                                on_click=self._play_audio,
                            ),
                            ft.Text(spans=[
                                ft.TextSpan("0:00"), ft.TextSpan("/"), ft.TextSpan("0:00")
                            ], weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.FAST_REWIND_ROUNDED, ft.Colors.GREY_600, size=25
                                ),
                                on_click=self._move_ten_seconds,
                                data="backward"
                            ),
                            ft.Slider(
                                value=0.01,
                                expand_loose=True,
                                expand=True,
                                on_change_end=self._move_song_to_slider,
                                active_color=ft.Colors.GREY_600,
                                inactive_color=ft.Colors.GREY_400,
                            ),
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.FAST_FORWARD_ROUNDED, ft.Colors.GREY_600, size=25
                                ),
                                on_click=self._move_ten_seconds,
                                data="forward"
                            )
                        ],
                    ),
                    border_radius=90,
                    padding=15,
                    height=75,
                    expand=True,
                    bgcolor=ft.Colors.with_opacity(0.7, ft.Colors.GREY_300),
                ),
            ],
            height=150,
            expand_loose=True,
            expand=True,
        )

        self.song_selector_row: ft.Row = ft.Row(
            [
                self.upload_cover_art_default_content,
                self.song_selector_info_column
            ],
        )

        self.sheet_selector = ft.Container(
            on_click=self._select_image_files,
            width=150,
            height=190,
            content=ft.Icon(ft.Icons.ADD, color=ft.Colors.GREY_800),
            alignment=ft.Alignment(0, 0),
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=3,
            ink=True,
            ink_color=ft.Colors.GREY
        )

        self.sheet_selector_row: ft.Row = ft.Row(
            [
                self.sheet_selector
            ],
            auto_scroll=False,
            scroll=ft.ScrollMode.ALWAYS,
            height=220,
        )

    def _initialize_song_info_textbox(self):
        self.song_name_textbox = ft.TextField(
            label="song name",
            expand=True,
        )

        self.song_album_textbox = ft.TextField(
            label="song album",
            expand=True,
        )

        self.song_artist_textbox = ft.TextField(
            label="song band",
            expand=True,
        )

        self.sheet_selector_max_size_text: ft.Text = ft.Text(
            f"0.0/{self.MAX_IMAGES_SIZE / self.MEGABYTE}MB",
            weight=ft.FontWeight.W_500
        )
        self.song_info_row: ft.Row = ft.Row(
            [
                self.song_name_textbox, self.song_album_textbox, self.song_artist_textbox
            ],
        )

    # only the sheet selector will visually keep track of the selected sizes, because the other 2 selectors only allow for
    # 1 selection at a time, meaning you dont need to keep track of them (either it is within the allowed limits, or it isn't)
    def _update_sheet_selector_max_size_text(self, update: bool = True):
        self.sheet_selector_max_size_text.value = f"{self.selected_images_size / self.MEGABYTE:.2f}/{self.MAX_IMAGES_SIZE / self.MEGABYTE:.2f}MB"

        if update:
            self.sheet_selector_max_size_text.update()

    def _initialize_genre_tag_textbox(self):
        self.selected_genres_textbox = TagInput(
            border_radius=5,
            border=ft.border.all(color=ft.Colors.BLACK),
            padding=ft.Padding(
                right=0, top=2, bottom=2, left=10
            ),
            tag_spacing=5,
            hint_text="add genre",
            hint_text_padding=1,
            allow_repeats=False,
            max_tags=5
        )

    def _clear_text_boxes(self, update: bool = True):
        """:param update: whether to automatically update the GUI to display the cleared state"""

        self.song_name_textbox.value = ""
        self.song_album_textbox.value = ""
        self.song_artist_textbox.value = ""
        self.selected_genres_textbox.clean()

        if update:
            self.song_info_row.update()

    # -----------------------------------------------------------------------------------------------------------------

    def _initialize_controls(self):
        self._initialize_sidebar_top()

        self._initialize_file_selectors()
        self._initialize_song_info_textbox()
        self._initialize_genre_tag_textbox()

        song_info_parameters = ft.Container(
            padding=ft.Padding(
                right=50,
                left=50,
                top=5,
                bottom=5
            ),
            expand=8,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Text(
                                "UPLOAD SONG",
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                                size=35),
                            expand=True,
                            expand_loose=True,
                            alignment=ft.Alignment(0, 0),
                            padding=5,
                            height=65,
                            bgcolor=ft.Colors.BLUE_800,
                            border_radius=10
                        ),

                        ft.Column(
                            [
                                ft.Column(
                                    [
                                        ft.Text("Details", weight=ft.FontWeight.BOLD),

                                        self.song_selector_row,

                                        ft.Divider(),
                                    ]
                                ),
                                ft.Column(
                                    [
                                        self.song_info_row,
                                        self.selected_genres_textbox,
                                    ]
                                ),
                            ],
                            spacing=20,
                        ),

                        ft.Divider(),

                        ft.Column(
                            [
                                ft.Text("Add Music Sheets", weight=ft.FontWeight.BOLD),
                                self.sheet_selector_max_size_text,
                                self.sheet_selector_row,
                            ]
                        ),

                        ft.Divider(),

                        # todo: clean up the code
                        ft.Row([
                            ft.Container(
                                height=55,
                                width=150,
                                border_radius=10,
                                content=ft.Text(
                                    "Clear information",
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.with_opacity(0.7, ft.Colors.RED_ACCENT_700),
                                    size=15,
                                ),
                                alignment=ft.Alignment(0, 0),
                                on_click=self._clear_page,
                            ),
                            ft.Container(
                                height=55,
                                width=200,
                                bgcolor=ft.Colors.BLUE_800,
                                border_radius=10,
                                content=ft.Text(
                                    "Upload",
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                                    size=15,
                                ),
                                alignment=ft.Alignment(0, 0),
                                on_click=self._upload_all_files
                            ),
                        ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    tight=False,
                    spacing=20,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    scroll=ft.ScrollMode.HIDDEN,
                ),
                expand=6,
                alignment=ft.Alignment(-1, -0.95)
            ),
            alignment=ft.Alignment(0, 0),
        )

        self.page_view = ft.Row(
            [
                self.sidebar,
                song_info_parameters,
            ],
            spacing=0,
            expand=True
        )

    def _show_file_too_big_error(self, max_size: int):
        max_size_string: str = f"{int(max_size / self.MEGABYTE)}MB"

        error_popup = ft.AlertDialog(
            open=True,
            shape=ft.RoundedRectangleBorder(radius=10),
            content=ft.Container(
                width=350,
                height=200,
                padding=15,
                content=ft.Column(
                    [
                        ft.Row(controls=[
                            ft.Icon(ft.Icons.FILE_UPLOAD_OFF, color=ft.Colors.BLACK, size=30)
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Text("This file exceeds the size limit", size=30, text_align=ft.TextAlign.CENTER),
                        ft.Text(f"The max file size for the file type you are trying to upload is {max_size_string}",
                                text_align=ft.TextAlign.CENTER)
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
            ),
        )

        self.append_error(error_popup)

    # todo: also make this restriction server side, meaning that the server checks that the sizes are also valid
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
    UploadPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
