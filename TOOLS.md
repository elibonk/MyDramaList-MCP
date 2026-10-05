# Tools

The server exposes 89 tools: 86 allowlisted SDK methods, an image upload tool,
and two local inspection tools. All writes require an app API bearer token.
Availability and raw payload semantics still depend on the private upstream API.

SDK methods with **kwargs expose them as one optional JSON object (filters/fields/params).
Extra keys cannot override named arguments. page starts at 1 and limit is capped at 100.
Read-only mode removes all write tools and image upload.

## search

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_search_titles` | read | upstream-dependent | `query` (required), `page`, `edge`, `synopsis`, `filters` |
| `mdl_search_top_dramas` | read | upstream-dependent | none |
| `mdl_search_people` | read | upstream-dependent | `query`, `page` |

- `mdl_search_titles`: Use filters for additional upstream search parameters; page starts at 1.

## titles

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_titles_get_title` | read | upstream-dependent | `title_id` (required) |
| `mdl_titles_get_comment_count` | read | upstream-dependent | `title_id` (required) |
| `mdl_titles_get_reviews` | read | upstream-dependent | `title_id` (required) |
| `mdl_titles_get_reviews_page` | read | upstream-dependent | `title_id` (required), `sort`, `page`, `limit` |
| `mdl_titles_get_recommendations` | read | upstream-dependent | `title_id` (required) |
| `mdl_titles_get_credits` | read | upstream-dependent | `title_id` (required) |
| `mdl_titles_get_genres` | read | upstream-dependent | none |
| `mdl_titles_search_tags` | read | upstream-dependent | `query` (required) |
| `mdl_titles_get_progress` | read | yes | `title_id` (required) |


## explore

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_explore_trending` | read | upstream-dependent | `params` |
| `mdl_explore_top_airing` | read | upstream-dependent | `params` |
| `mdl_explore_upcoming` | read | upstream-dependent | `params` |
| `mdl_explore_recommended` | read | upstream-dependent | `params` |
| `mdl_explore_currently_watching` | read | upstream-dependent | `params` |
| `mdl_explore_top_movies` | read | upstream-dependent | `params` |


## users

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_users_get_user_info` | read | upstream-dependent | `user_id` (required) |
| `mdl_users_get_person` | read | upstream-dependent | `person_id` (required) |
| `mdl_users_get_person_credits` | read | upstream-dependent | `person_id` (required) |
| `mdl_users_get_user_stats` | read | upstream-dependent | `user_id` (required) |
| `mdl_users_get_user_watchlist` | read | yes | `params` |
| `mdl_users_like_person` | write | yes | `person_id` (required), `liked` |


## reviews

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_reviews_get` | read | upstream-dependent | `review_id` (required) |
| `mdl_reviews_check_already_wrote` | read | yes | `title_id` (required) |
| `mdl_reviews_submit` | write | yes | `review` (required), `headline` (required), `completed`, `dropped`, `episodes_seen`, `parent_id` (required), `lang_iso`, `story`, `acting`, `music`, `rewatch`, `overall`, `spoiler` |
| `mdl_reviews_edit` | write | yes | `review_id` (required), `fields` |
| `mdl_reviews_delete` | write | yes | `review_id` (required) |
| `mdl_reviews_vote` | write | yes | `review_id` (required), `direction` (required) |

- `mdl_reviews_submit`: parent_id identifies the title. Publishes a review on MyDramaList.
- `mdl_reviews_edit`: fields is an upstream patch object; rating edits use a nested ratings object.

## comments

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_comments_list` | read | upstream-dependent | `ptype` (required), `pid` (required), `page`, `params` |
| `mdl_comments_post` | write | yes | `pid` (required), `ptype` (required), `message` (required), `reply_to`, `spoiler` |
| `mdl_comments_update` | write | yes | `comment_id` (required), `message` (required), `spoiler` |
| `mdl_comments_delete` | write | yes | `comment_id` (required) |
| `mdl_comments_like` | write | yes | `comment_id` (required), `liked` |

- `mdl_comments_post`: Publishes a comment. ptype is the upstream content type (clist for lists).

## custom_lists

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_custom_lists_get_user_lists` | read | upstream-dependent | `user_id` (required), `page`, `limit` |
| `mdl_custom_lists_popular` | read | upstream-dependent | `page`, `limit` |
| `mdl_custom_lists_recent_activity` | read | upstream-dependent | `page`, `limit` |
| `mdl_custom_lists_trending` | read | upstream-dependent | `page`, `limit` |
| `mdl_custom_lists_featured` | read | upstream-dependent | `page`, `limit` |
| `mdl_custom_lists_get_detail` | read | upstream-dependent | `list_id` (required) |
| `mdl_custom_lists_get_votes` | read | upstream-dependent | `list_id` (required) |
| `mdl_custom_lists_get_watch_status` | read | upstream-dependent | `list_id` (required) |
| `mdl_custom_lists_list_comments` | read | upstream-dependent | `list_id` (required), `page`, `params` |
| `mdl_custom_lists_friends_voted` | read | yes | `page`, `limit` |
| `mdl_custom_lists_i_voted` | read | yes | `page`, `limit` |
| `mdl_custom_lists_create` | write | yes | `name` (required), `description`, `list_type`, `type`, `sort_by`, `vote_limit`, `max_num_items`, `add_permission` |
| `mdl_custom_lists_edit` | write | yes | `list_id` (required), `fields` |
| `mdl_custom_lists_delete` | write | yes | `list_id` (required) |
| `mdl_custom_lists_set_votes` | write | yes | `list_id` (required), `votes` (required) |
| `mdl_custom_lists_add_item` | write | yes | `list_id` (required), `entry_id` (required) |
| `mdl_custom_lists_remove_item` | write | yes | `list_id` (required), `item_id` (required) |
| `mdl_custom_lists_sort_item` | write | yes | `list_id` (required), `item_id` (required), `order` (required) |
| `mdl_custom_lists_like` | write | yes | `list_id` (required), `liked` |
| `mdl_custom_lists_post_comment` | write | yes | `list_id` (required), `message` (required), `reply_to`, `spoiler` |
| `mdl_custom_lists_update_comment` | write | yes | `comment_id` (required), `message` (required), `spoiler` |

- `mdl_custom_lists_edit`: fields is an upstream patch object, e.g. name and description.

## feeds

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_feeds_fetch` | read | upstream-dependent | `params` |
| `mdl_feeds_get` | read | upstream-dependent | `feed_id` (required) |
| `mdl_feeds_create` | write | yes | `message` (required), `privacy`, `spoiler`, `tag_id`, `tag_type`, `attachments`, `embed_id`, `group_id` |
| `mdl_feeds_edit` | write | yes | `feed_id` (required), `message` (required), `spoiler`, `tag_id`, `tag_type`, `attachments`, `embed_id` |
| `mdl_feeds_delete` | write | yes | `feed_id` (required) |
| `mdl_feeds_hide` | write | yes | `feed_id` (required) |
| `mdl_feeds_like` | write | yes | `feed_id` (required), `liked` |

- `mdl_feeds_create`: Publishes an activity post; privacy defaults to public.

## articles

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_articles_get` | read | upstream-dependent | `article_id` (required) |
| `mdl_articles_featured` | read | upstream-dependent | `page` |
| `mdl_articles_like` | write | yes | `article_id` (required), `liked` |


## groups

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_groups_get` | read | upstream-dependent | `group_id` (required) |


## calendar

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_calendar_quarter` | read | upstream-dependent | `year` (required), `quarter` (required) |
| `mdl_calendar_episodes` | read | yes | none |

- `mdl_calendar_quarter`: quarter is the upstream quarter identifier; use documented API values.

## leaderboard

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_leaderboard_get` | read | upstream-dependent | `time_period` |


## awards

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_awards_list` | read | upstream-dependent | none |


## account

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_account_get_profile` | read | yes | none |
| `mdl_account_get_privacy` | read | yes | none |
| `mdl_account_get_activities` | read | yes | none |
| `mdl_account_update_profile_info` | write | yes | `display_name`, `location`, `gender`, `dob`, `dob_privacy` |
| `mdl_account_update_privacy` | write | yes | `profile_feed` (required) |
| `mdl_account_map_profile_picture` | write | yes | `picture` (required) |

- `mdl_account_update_profile_info`: Only non-null fields supplied are sent; omitted fields are preserved.
- `mdl_account_map_profile_picture`: Use the filename returned by mdl_upload_image.

## watchlist

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_watchlist_fetch` | read | yes | `status` (required), `last_updated_at` |
| `mdl_watchlist_fetch_page` | read | yes | `status` (required), `page` |
| `mdl_watchlist_get_last_activities` | read | yes | none |
| `mdl_watchlist_add` | write | yes | `item` (required) |
| `mdl_watchlist_remove` | write | yes | `ids` (required) |

- `mdl_watchlist_add`: Add or update a watchlist entry, including episode progress, rating, dates and notes. item is the upstream sync JSON object. The package does not define a typed request model or numeric status mapping. Use confirmed API fields; do not invent a status code.
- `mdl_watchlist_remove`: Remove entries by title IDs, not list entry IDs.

## notifications

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_notifications_fetch` | read | yes | `page`, `limit` |
| `mdl_notifications_clear` | write | yes | `notification_id` (required) |
| `mdl_notifications_clear_all` | write | yes | none |


## friends

| Tool | Mode | Auth required | Arguments |
| --- | --- | --- | --- |
| `mdl_friends_requests` | read | yes | `page` |


## Additional tools

- `mdl_server_status`: local authentication presence and server mode; never returns tokens.
- `mdl_capabilities`: available methods and known limitations.
- `mdl_upload_image`: base64 JPEG/PNG/WebP upload, max 5 MiB, target profile or feed. Auth required.

## Tool result format

Success uses `{"ok":true,"data":...}` in both text and MCP structured content.
Failure uses `{"ok":false,"error":{"code":"...","message":"..."}}` with MCP `isError=true`.
An `ok` result means the SDK call completed and parsed; inspect the upstream acknowledgement
inside data to confirm the requested change (including partial success or not_found entries).
Validation failures are standard MCP tool errors. Write failures are never retried automatically.
