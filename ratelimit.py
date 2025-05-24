import time

rate_limit_threshold: dict[str, tuple[int, int]] = {
    "song/download/preview": (3, 1),
    "song/recommended/download/preview": (3, 1),
    "song/recent/download/preview": (3, 1),
    "song/download/preview/resend": (5, 1),

    "song/download/audio": (3, 1),
    "song/download/sheets": (3, 1),

    "song/genres": (10, 1),
    "song/genres/download/preview": (3, 1),

    "song/comments": (10, 1),
    "song/comments/upload": (5, 2),

    "song/search": (100, 3),

    "song/comment/delete": (5, 1),
    "song/delete": (2, 1),

    "user/statistics": (5, 1),
    "user/edit/display": (5, 1),
    "user/logout": (2, 1),
    "user/delete": (2, 5),
}
"""dict[endpoint] -> tuple[number of requests, per number of seconds]"""


class RateLimits:
    def __init__(self):
        self.user_rate_limits: dict[tuple[str, str], list[float]] = {}
        """
        dict[tuple[user ID, endpoint] -> list[endpoint requested at timestamps]
        """

    def _calculate_threshold_limit(self, user_id: str, endpoint: str, how_many_requests: int, time_window_seconds: int) -> bool:
        """calculates if the user reached the rate limit threshold"""
        current_time = time.time()

        user_threshold_list = self.user_rate_limits.get((user_id, endpoint), [])
        if not user_threshold_list:
            self.user_rate_limits[(user_id, endpoint)] = [current_time]
            return False

        # we calculate how many of the current timestamps exceed that allowed value
        threshold_reached_list: list[float] = [
            timestamp for timestamp in user_threshold_list
            if current_time - timestamp <= time_window_seconds
        ]

        # we change the old list to the new values list, so that we won't have to calculate old values and save on memory
        # and time
        self.user_rate_limits[(user_id, endpoint)] = threshold_reached_list

        has_passed_threshold = len(threshold_reached_list) >= how_many_requests

        # this means that the rate limit was exceeded, we do not add the new request to the list as no action will be
        # performed
        if has_passed_threshold:
            return True

        # we add the current time to the request list for the user as the server will now perform an action based on the
        # request
        threshold_reached_list.append(current_time)

        return False

    def has_reached_threshold(self, user_id: str, endpoint: str) -> bool:
        threshold_requests, threshold_seconds = rate_limit_threshold.get(endpoint, (None, None))

        if not threshold_requests or not threshold_seconds:
            return False

        return self._calculate_threshold_limit(
            user_id, endpoint, threshold_requests, threshold_seconds
        )
