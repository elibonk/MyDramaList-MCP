"""Explicit allowlist, so upstream additions cannot silently expose new powers.

Each method retains the installed SDK's typed arguments. **kwargs becomes a single
JSON object, rather than an untyped arbitrary HTTP endpoint.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    group: str
    method: str
    write: bool = False
    private: bool = False
    destructive: bool = False
    note: str = ""

    @property
    def name(self) -> str:
        return f"mdl_{self.group}_{self.method}"


READS = {
    "search": "titles top_dramas people",
    "titles": "get_title get_comment_count get_reviews get_reviews_page get_recommendations "
    "get_credits get_genres search_tags",
    "explore": "trending top_airing upcoming recommended currently_watching top_movies",
    "users": "get_user_info get_person get_person_credits get_user_stats",
    "reviews": "get",
    "comments": "list",
    "custom_lists": "get_user_lists popular recent_activity trending featured get_detail "
    "get_votes get_watch_status list_comments",
    "feeds": "fetch get",
    "articles": "get featured",
    "groups": "get",
    "calendar": "quarter",
    "leaderboard": "get",
    "awards": "list",
}
PRIVATE_READS = {
    "account": "get_profile get_privacy get_activities",
    "titles": "get_progress",
    "users": "get_user_watchlist",
    "watchlist": "fetch fetch_page get_last_activities",
    "reviews": "check_already_wrote",
    "custom_lists": "friends_voted i_voted",
    "notifications": "fetch",
    "calendar": "episodes",
    "friends": "requests",
}
WRITES = {
    "account": "update_profile_info update_privacy map_profile_picture",
    "users": "like_person",
    "watchlist": "add remove",
    "reviews": "submit edit delete vote",
    "comments": "post update delete like",
    "custom_lists": "create edit delete set_votes add_item remove_item sort_item like "
    "post_comment update_comment",
    "feeds": "create edit delete hide like",
    "articles": "like",
    "notifications": "clear clear_all",
}
NOTES = {
    (
        "search",
        "titles",
    ): "Use filters for additional upstream search parameters; page starts at 1.",
    ("watchlist", "add"): (
        "Add or update a watchlist entry, including episode progress, rating, dates and notes. "
        "item is the upstream sync JSON object. The package does not define a typed request model "
        "or numeric status mapping. Use confirmed API fields; do not invent a status code."
    ),
    ("watchlist", "remove"): "Remove entries by title IDs, not list entry IDs.",
    ("reviews", "submit"): "parent_id identifies the title. Publishes a review on MyDramaList.",
    (
        "reviews",
        "edit",
    ): "fields is an upstream patch object; rating edits use a nested ratings object.",
    (
        "comments",
        "post",
    ): "Publishes a comment. ptype is the upstream content type (clist for lists).",
    ("custom_lists", "edit"): "fields is an upstream patch object, e.g. name and description.",
    ("feeds", "create"): "Publishes an activity post; privacy defaults to public.",
    (
        "account",
        "update_profile_info",
    ): "Only non-null fields supplied are sent; omitted fields are preserved.",
    ("account", "map_profile_picture"): "Use the filename returned by mdl_upload_image.",
    (
        "calendar",
        "quarter",
    ): "quarter is the upstream quarter identifier; use documented API values.",
}


def operations() -> list[Operation]:
    result = []
    for table, write, private in [
        (READS, False, False),
        (PRIVATE_READS, False, True),
        (WRITES, True, True),
    ]:
        for group, methods in table.items():
            for method in methods.split():
                result.append(
                    Operation(
                        group,
                        method,
                        write,
                        private,
                        destructive=method
                        in {"delete", "remove", "remove_item", "clear", "clear_all"},
                        note=NOTES.get((group, method), ""),
                    )
                )
    return result
