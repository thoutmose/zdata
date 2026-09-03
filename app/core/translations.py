"""English/French translation catalog for every user-facing string in the app.

Populated by grepping every `t("...")` call site so no key is ever guessed —
see `app/core/i18n.py::t`. Keys are dotted and namespaced by page
(`"donations.kpi.total_raised"`), plus a `"common.*"` namespace for strings
shared across pages. Raw data values (streamer names, category names, French
goal titles already in the DB) are never translated here — only UI chrome.
"""

from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # --- common ---
        "common.mock_data_banner": (
            "Showing **sample data** — connect a database "
            "(`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) to see live figures."
        ),
        "common.no_data_in_range": "No data in the selected range.",
        "common.view_data": "View underlying data",
        "common.download_csv": "⬇️ Download CSV",
        "common.how_to_read": "💡 How to read this chart",
        "period.label": "Period",
        "period.last_hour": "Last hour",
        "period.last_6h": "Last 6h",
        "period.last_24h": "Last 24h",
        "period.all": "All event",
        "common.per_hour": "{unit} / hour",
        "common.unit.messages": "messages",
        "common.unit.viewers": "viewers",
        "common.unit.avg_viewers": "avg. viewers",
        "common.unit.channels": "channels",
        "common.unit.channel_hours": "channel-hours",
        "common.unit.chatters": "chatters",
        "common.unit.goals": "goals",
        "common.badge.subscriber": "Subscriber",
        "common.badge.vip": "VIP",
        "common.badge.moderator": "Moderator",
        "common.badge.plain_viewer": "Plain viewer",
        "common.chatter_profile.loyal": "Loyal (single-channel)",
        "common.chatter_profile.multi_streamer": "Multi-streamer",
        "common.chatter_profile.semi_nomad": "Semi-nomad",
        "common.chatter_profile.nomad": "Nomad",
        "common.chatter_profile.caption": (
            "Loyal chatters only chat in one channel; nomads spread their messages "
            "across many channels during the event."
        ),
        # --- global search (sidebar, every page) ---
        "search.label": "🔍 Search",
        "search.placeholder": "Streamers, categories, titles, emotes, chatters...",
        "search.no_results": 'No results for "{query}".',
        "search.more_results": "+{count} more — refine your search to narrow it down.",
        "search.type.streamer": "Streamer",
        "search.type.category": "Category",
        "search.type.title": "Stream title",
        "search.type.emote": "Emote",
        "search.type.chatter": "Chatter",
        # --- page titles (used in both the sidebar page header and the home cards) ---
        "donations.title": "Donations",
        "streamers.title": "Streamers",
        "games.title": "Games",
        "goals.title": "Donation Goals",
        "chat.title": "Live Chat",
        "community.title": "Community",
        "tracker.title": "Donation Tracker",
        # --- home ---
        "home.title": "ZEvent Dataviz",
        "home.tagline": "Data-modeling dashboards for the ZEvent charity gaming marathon.",
        "home.db_error": (
            "Database credentials are configured but the connection failed. "
            "Check `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` and network access."
        ),
        "home.about_body": (
            "This app streams and analyzes the live data of the latest ZEvent occurrence "
            "(**September 3-6, 2026**) — a French charity gaming marathon where streamers "
            "raise donations for a cause. It covers four data domains straight from the "
            "warehouse as the event happens: **donations**, **streamers**, **live chat**, "
            "and **chatters**.\n\n"
            "It's read-only and connects to a shared PostgreSQL warehouse (via PgBouncer) "
            "modeled with dbt across `raw` → `stg` → `int` → `marts` schemas, fed by two "
            "independent pipelines: ZEvent's own donations/goals site, and Twitch's "
            "stream/chat metadata."
        ),
        "home.kpi_heading": "Event snapshot",
        "home.kpi.duration": "Donation tracking span",
        "home.kpi.duration_value": "{hours} h",
        "home.kpi.streamers": "Streamers",
        "home.kpi.chatters": "Chatters",
        "home.kpi.messages": "Chat messages",
        "home.kpi.peak_viewers": "Peak concurrent viewers",
        "home.pages_heading": "Pages",
        "home.related_projects": (
            "**Related projects** — this app is part of a small ecosystem: "
            "`zevent-analysis` (deeper offline analysis), `zevent-db` (the warehouse this "
            "app reads from), and `zevent-infra-monitoring` (pipeline/infra monitoring). "
            "This dashboard is currently the only one of the four with a working deliverable."
        ),
        # --- donations ---
        "donations.description": (
            "Cumulative donations over the course of the event, how the pace evolves hour "
            "by hour, and who's moving on the leaderboard."
        ),
        "donations.no_data": "No donation data available yet.",
        "donations.filters": "Filters",
        "donations.kpi.total_raised": "Total raised",
        "donations.kpi.active_streamers": "Active streamers (last hour)",
        "donations.kpi.best_hour": "Best hour",
        "donations.chart.cumulative": "Cumulative donations",
        "donations.chart.pace": "Donation pace (per hour)",
        "donations.phases_heading": "Event phases",
        "donations.chart.by_phase": "Donations by event phase",
        "donations.phases_caption": (
            "The event is split into three phases (opening, middle, final push). "
            "This fills in as the event actually progresses through them."
        ),
        "donations.movers_heading": "Leaderboard movers",
        "donations.movers_caption": "Streamers with the biggest recent donation-rank swings (up or down).",
        "donations.quality_heading": "Data quality",
        "donations.quality_no_data": "No reconciliation data available yet.",
        "donations.quality_ok": "Donation totals reconciled (Δ = {divergence} €) as of {time}.",
        "donations.quality_bad": "Donation totals diverge by {divergence} € as of {time}.",
        "donations.quality_caption": (
            "This compares the event-wide donation total against the sum of individual "
            "streamer totals at the same snapshot — a basic data-integrity check."
        ),
        "donations.explain.cumulative": (
            "The running total of donations across every streamer, from the start of the "
            "event to now. Always flat or rising — it never goes down."
        ),
        "donations.explain.pace": (
            "How much was raised in each individual hour (not cumulative). Spikes usually "
            "line up with incentives, milestones, or a popular streamer going live."
        ),
        "donations.explain.phase": (
            "Donations grouped into the event's three phases (opening, middle, final push), "
            "so you can see which stretch of the event raised the most."
        ),
        "donations.by_activity_heading": "Donations by activity",
        "donations.no_activity_data": "No activity-attributed donation data available yet.",
        "donations.by_activity_caption": (
            "Each hour's donations attributed to whichever Twitch category a channel was "
            "streaming that hour — an hour-grain approximation, same as the stream-title "
            "leaderboard on the Games page."
        ),
        "donations.chart.by_activity": "Donations by Twitch category",
        "donations.explain.by_activity": (
            "Which activities (Twitch categories) donations were raised during — useful for "
            "spotting whether a particular game or segment (e.g. a charity challenge) drove "
            "disproportionately more giving."
        ),
        # --- streamers ---
        "streamers.description": (
            "Who raised how much, with audience, engagement, and a per-streamer profile drill-down."
        ),
        "streamers.no_data": "No streamer data available yet.",
        "streamers.filters": "Filters",
        "streamers.search": "Search by name",
        "streamers.category_filter": "Filter by top category",
        "streamers.min_viewers": "Minimum avg. viewers",
        "streamers.rank_by": "Rank streamers by",
        "streamers.rank.donations": "Donations",
        "streamers.rank.engagement": "Chat engagement (messages)",
        "streamers.rank.audience": "Audience (avg. viewers)",
        "streamers.top_n": "Show top N",
        "streamers.kpi.top": "Top by {metric}",
        "streamers.kpi.total_raised": "Total raised (shown)",
        "streamers.kpi.total_messages": "Total chat messages (shown)",
        "streamers.chart.ranked": "Streamers by {metric}",
        "streamers.correlation_heading": "Audience vs. engagement",
        "streamers.correlation_caption": (
            "Each point is a streamer — bubble size is donations raised. Useful for spotting "
            "high-viewer/low-chat (or the reverse) outliers."
        ),
        "streamers.chart.correlation": "Avg. viewers vs. chat messages",
        "streamers.profile_heading": "Streamer profile",
        "streamers.pick_streamer": "Pick a streamer for a detailed profile",
        "streamers.kpi.peak_viewers": "Peak viewers",
        "streamers.kpi.uptime": "Uptime",
        "streamers.kpi.top_category": "Top category",
        "streamers.kpi.unique_chatters": "Unique chatters",
        "streamers.uptime_quirk": "100%+ (data quirk)",
        "streamers.chart.loyalty_mix": "{streamer}'s chatter loyalty mix",
        "streamers.no_diurnal_data": "No hourly viewer pattern available yet for this streamer.",
        "streamers.chart.diurnal": "Hourly viewer pattern vs. event average",
        "streamers.hour_of_day": "hour of day (Europe/Paris)",
        "streamers.event_average": "Event average",
        "streamers.explain.ranked": (
            "The top N streamers ranked by whichever metric is selected above — donations, "
            "chat messages, or average viewers. One bar per streamer, longest first."
        ),
        "streamers.explain.correlation": (
            "Each point is a streamer: horizontal position is average viewers, vertical "
            "position is chat messages, and bubble size is donations raised. A point far "
            "from the rest is worth a closer look — e.g. lots of viewers but a quiet chat."
        ),
        "streamers.explain.loyalty_mix": (
            "How many of this streamer's chatters only chat here (loyal) vs. also chat on "
            "other channels during the event (multi-streamer, semi-nomad, nomad)."
        ),
        "streamers.explain.diurnal": (
            "Average viewers by hour of day for this streamer (solid line) vs. the "
            "event-wide average (dotted) — shows whether this streamer's peak hours line "
            "up with, or differ from, everyone else's."
        ),
        # --- games ---
        "games.description": (
            "Which categories are being played, concurrent viewership over time, and recent sessions."
        ),
        "games.filters": "Filters",
        "games.kpi.concurrent_now": "Concurrent viewers now",
        "games.kpi.channels_now": "Live channels now",
        "games.kpi.peak_concurrent": "Peak concurrent viewers",
        "games.chart.viewership": "Event-wide concurrent viewership",
        "games.chart.live_channels": "Live channels over time",
        "games.no_viewership": "No viewership data available yet.",
        "games.categories_heading": "Categories",
        "games.category_filter": "Filter categories",
        "games.chart.by_category": "Channel-hours by category",
        "games.no_categories": "No category data available yet.",
        "games.sessions_heading": "Recent stream sessions",
        "games.no_sessions": "No stream sessions recorded yet.",
        "games.titles_heading": "Stream title leaderboard",
        "games.no_titles": "No stream-title data available yet.",
        "games.titles_caption": (
            "Messages and donations attributed to each title by matching channel + hour — an "
            "hour-grain approximation, since a mid-hour title change would split that hour's "
            "activity across titles."
        ),
        "games.titles_rank_by": "Rank titles by",
        "games.titles_by_messages": "Messages",
        "games.titles_by_donations": "Donations",
        "games.chart.titles": "Top stream titles",
        "games.explain.viewership": (
            "Total concurrent viewers across every live channel, over time — a proxy for "
            "the event's overall audience at any given moment."
        ),
        "games.explain.live_channels": (
            "How many channels were simultaneously live, hour by hour."
        ),
        "games.explain.by_category": (
            "Total channel-hours spent playing each category — a category played by many "
            "channels for a short time can outrank one played by few for a long time."
        ),
        "games.explain.titles": (
            "Stream titles ranked by chat messages or donations (pick which above) — an "
            "hour-grain approximation of which specific moments drove the most activity."
        ),
        # --- goals ---
        "goals.description": (
            "The milestone goals ('objectifs') streamers set for donations — by category and by streamer."
        ),
        "goals.no_data": "No donation-goal data available yet.",
        "goals.caveat": (
            "⚠️ Goal amounts are chosen by streamers and often intentionally absurd "
            "(jokes in the hundreds of millions of euros exist). This page shows "
            "**counts**, not summed euro totals, so a handful of joke goals can't "
            "skew the picture."
        ),
        "goals.kpi.total_goals": "Total goals",
        "goals.kpi.categories": "Categories",
        "goals.kpi.streamers": "Participating streamers",
        "goals.category_heading": "Goals by category",
        "goals.chart.by_category": "Goals by category",
        "goals.chart.top_setters": "Streamers with the most goals set",
        "goals.distribution_heading": "Explore the amount distribution",
        "goals.no_amounts": "No goal-amount data available yet.",
        "goals.distribution_caption": (
            "Raw goal amounts, log-scaled — the right tail is almost entirely jokes. "
            "Pick your own cutoff instead of trusting a single hardcoded threshold."
        ),
        "goals.cutoff_slider": 'Treat goals below this amount as "realistic"',
        "goals.chart.distribution": "Goal amount distribution (log scale)",
        "goals.log_amount_axis": "log₁₀(amount in €)",
        "goals.kpi.below_cutoff": "Below cutoff",
        "goals.kpi.above_cutoff": "Above cutoff (likely jokes)",
        "goals.cutoff_caption": 'Move the slider above to change what counts as "realistic".',
        "goals.explain.by_category": (
            "How many goals streamers set in each category (recurring, single-donation "
            "threshold, etc.) — counts, not summed amounts, since joke amounts would dominate."
        ),
        "goals.explain.top_setters": (
            "The streamers who set the most donation goals, regardless of amount."
        ),
        "goals.explain.distribution": (
            "Every 'donation'-type goal's raw amount, log-scaled so both realistic and "
            "joke-sized goals fit on one axis. The dashed line marks your cutoff slider."
        ),
        # --- chat ---
        "chat.description": "Message volume over time, the busiest channels, and the most-used emotes.",
        "chat.no_data": "No chat data available yet.",
        "chat.filters": "Filters",
        "chat.kpi.messages_this_hour": "Messages this hour",
        "chat.kpi.chatters_this_hour": "Unique chatters this hour",
        "chat.kpi.total_messages": "Total messages (event)",
        "chat.chart.activity": "Chat messages per hour (all channels)",
        "chat.engagement_heading": "Chat engagement rate",
        "chat.engagement_caption": (
            "Messages per minute per 100 viewers — a proxy for enthusiasm/engagement that "
            "adjusts for audience size. There's no sentiment/emotion data in the warehouse, "
            'so this is the closest real signal to "how excited is chat right now."'
        ),
        "chat.no_engagement": "No engagement-rate data available yet (needs viewers > 0).",
        "chat.chart.engagement": "Chat engagement rate over time",
        "chat.engagement_axis": "messages / min / 100 viewers",
        "chat.heatmap_heading": "Activity heatmap",
        "chat.no_heatmap": "No channel-level chat data available yet.",
        "chat.channel_filter": "Filter channels",
        "chat.heatmap_caption": "Darker = more messages in that channel, that hour.",
        "chat.chart.heatmap": "Messages by channel and hour",
        "chat.channels_heading": "Busiest channels",
        "chat.no_channels": "No channel-level chat data available yet.",
        "chat.channels_caption": (
            "Message composition by badge — a channel with a high subscriber/moderator "
            "share has a more established community than raw volume alone shows."
        ),
        "chat.chart.composition": "Message composition by channel",
        "chat.emotes_heading": "Top emotes",
        "chat.no_emotes": "No emote data available yet.",
        "chat.emotes_unnamed_caveat": (
            "⚠️ The emote catalog isn't populated for this event yet, so emotes are shown by a "
            "shortened raw ID instead of their name — this fills in automatically once it is."
        ),
        "chat.uses_axis": "uses",
        "chat.explain.activity": (
            "Total chat messages per hour across every channel — a quick read on when "
            "the event's overall chat activity was highest."
        ),
        "chat.explain.engagement": (
            "Messages per minute per 100 viewers, averaged across channels — this adjusts "
            "for audience size, so a small channel with a very active chat isn't hidden by "
            "a big channel's raw message count."
        ),
        "chat.explain.heatmap": (
            "One cell per channel x hour; darker means more messages. Good for spotting "
            "which channels were active at which times, at a glance."
        ),
        "chat.explain.composition": (
            "Each channel's messages split by who sent them (subscriber, VIP, moderator, "
            "plain viewer) — a high subscriber/moderator share suggests an established "
            "community, not just raw volume."
        ),
        "chat.explain.emotes": (
            "The most-used emotes across the event, by usage count. Emotes not yet in the "
            "catalog are shown by a shortened id instead of their real code (see the note "
            "above the chart, if any are unnamed)."
        ),
        # --- community ---
        "community.description": (
            "Who's chatting, how loyal they are to a single channel, and which channels "
            "share an audience."
        ),
        "community.no_data": "No chatter data available yet.",
        "community.kpi.total_chatters": "Total chatters",
        "community.kpi.multi_channel": "Multi-channel chatters",
        "community.kpi.loyal_share": "Share loyal to one channel",
        "community.growth_heading": "Chatter growth",
        "community.growth_caption": "Cumulative distinct chatters seen, over time.",
        "community.chart.growth": "Cumulative chatters over time",
        "community.cumulative_chatters": "cumulative chatters",
        "community.hourly_network_heading": "Chatter community, hour by hour",
        "community.hourly_network_caption": (
            "Each edge means two channels share chatters that hour — thicker/darker means "
            "more shared chatters. Pick an hour to see how the community network evolved."
        ),
        "community.hour_picker": "Hour",
        "community.no_hourly_network": "No hourly network data available yet.",
        "community.chart.hourly_network": "Shared-audience network at {hour}",
        "community.chart.loyalty_mix": "Chatter loyalty mix",
        "community.chart.account_age": "Chatters by Twitch account age",
        "community.age.new": "New (<30d)",
        "community.age.month_to_year": "1 month - 1 year",
        "community.age.one_to_three": "1 - 3 years",
        "community.age.three_plus": "3+ years",
        "community.age.unknown": "Unknown",
        "community.age_caption": "Account age is unknown for chatters whose profile couldn't be fetched.",
        "community.chatters_heading": "Most active chatters",
        "community.no_chatters": "No chatter leaderboard available yet.",
        "community.chatters_caption": (
            'Some "top chatters" are bots (e.g. moderation bots) rather than people — '
            "the channel is shown alongside so that's visible without extra guesswork."
        ),
        "community.channel_filter": "Filter by channel",
        "community.hide_bots": "Hide likely bots",
        "community.top_n": "Show top N",
        "community.chart.top_chatters": "Top chatters by message count",
        "community.network_heading": "Shared audiences between channels",
        "community.no_network": "No cross-channel audience overlap detected yet.",
        "community.network_caption": (
            "Every channel pair that shares chatters, as a network graph — thicker/darker "
            "edges mean more shared chatters, and each channel keeps its own fixed node "
            "color, same as the hour-by-hour graph above."
        ),
        "community.chart.network": "Shared-audience network",
        "community.explain.growth": (
            "The cumulative count of distinct chatters seen so far, over time — always "
            "flat or rising."
        ),
        "community.explain.hourly_network": (
            "One node per channel, one edge per pair of channels that shared chatters "
            "that hour — thicker/darker edges mean more shared chatters. Each node has its "
            "own fixed color, so the same channel is easy to spot across different hours."
        ),
        "community.explain.loyalty_mix": (
            "How many chatters only ever chat in one channel (loyal) vs. spread their "
            "messages across several (multi-streamer, semi-nomad, nomad)."
        ),
        "community.explain.account_age": (
            "Chatters bucketed by how old their Twitch account is — a very new account "
            "isn't necessarily a bot, but a spike in brand-new accounts can be worth a look."
        ),
        "community.explain.top_chatters": (
            "The most active chatters by message count. Some top chatters are moderation "
            'bots rather than people — use "Hide likely bots" to focus on real viewers, '
            "or the channel column to spot them yourself."
        ),
        "community.explain.network": (
            "One node per channel, sized by how many other channels it shares an audience "
            "with; one edge per channel pair, thicker/darker for more shared chatters. "
            "Event-wide, unlike the hour-by-hour graph above it."
        ),
        # --- tracker ---
        "tracker.description": (
            "Track a streamer's donation goals: when each one started, when it was "
            "completed, and how long it took."
        ),
        "tracker.global_heading": "Global overview",
        "tracker.no_global_data": "No trackable donation goals across streamers yet.",
        "tracker.global_caption": "Goal-completion progress across every streamer with 'donation'-type goals.",
        "tracker.chart.top_completers": "Streamers with the most completed goals",
        "tracker.per_streamer_heading": "Per streamer",
        "tracker.no_streamers": "No streamer data available yet.",
        "tracker.pick_streamer": "Pick a streamer",
        "tracker.no_goals": "No trackable donation goals for this streamer yet.",
        "tracker.kpi.total": "Goals tracked",
        "tracker.kpi.done": "Done",
        "tracker.kpi.in_progress": "In progress",
        "tracker.kpi.not_started": "Not started",
        "tracker.status.done": "✅ Done",
        "tracker.status.in_progress": "🟡 In progress",
        "tracker.status.not_started": "⚪ Not started",
        "tracker.view_picker": "View",
        "tracker.view.timeline": "Timeline",
        "tracker.view.duration_bar": "Time-to-complete",
        "tracker.timeline_caption": (
            "A goal starts when {streamer}'s total donations reached the previous goal's "
            "amount, and completes when they reach its own amount."
        ),
        "tracker.chart.timeline": "Goal timeline",
        "tracker.timeline_axis": "time",
        "tracker.no_timeline": "No goal has started yet for this streamer.",
        "tracker.duration_bar_caption": "How long each completed goal took, ranked.",
        "tracker.no_completed_goals": "No completed goals yet for this streamer.",
        "tracker.chart.duration_bar": "Time to complete each goal",
        "tracker.duration_axis": "hours",
        "tracker.table_heading": "All goals",
        "tracker.table_caption": "Every goal, with exact duration in hours and seconds.",
        "tracker.column.goal": "Goal",
        "tracker.column.amount": "Amount",
        "tracker.column.status": "Status",
        "tracker.column.started": "Started",
        "tracker.column.completed": "Completed",
        "tracker.column.duration": "Duration",
        "tracker.column.duration_hours": "Duration (hours)",
        "tracker.column.duration_seconds": "Duration (seconds)",
        "tracker.explain.top_completers": (
            "The streamers who have completed the most donation goals so far, ranked."
        ),
        "tracker.explain.timeline": (
            "Each bar spans from when a goal started (the previous goal completed) to "
            "when it completed, or to now if it's still in progress. Bars for the same "
            "streamer never overlap in time, since one goal starts where the last ended."
        ),
        "tracker.explain.duration_bar": (
            "How long each completed goal took, from start to completion, ranked longest "
            "to shortest."
        ),
        # --- chatters ---
        "chatters.title": "Chatters",
        "chatters.description": (
            "Per-chatter analytics: loyalty, activity, and a profile drill-down — like the "
            "Streamers page, but for individual chatters."
        ),
        "chatters.no_data": "No chatter data available yet.",
        "chatters.filters": "Filters",
        "chatters.search": "Search by name",
        "chatters.profile_filter": "Filter by loyalty profile",
        "chatters.age_filter": "Filter by account age",
        "chatters.min_messages": "Minimum messages",
        "chatters.hide_bots": "Hide likely bots",
        "chatters.rank_by": "Rank chatters by",
        "chatters.rank.messages": "Messages",
        "chatters.rank.channels": "Channels chatted in",
        "chatters.top_n": "Show top N",
        "chatters.kpi.total": "Chatters (filtered)",
        "chatters.kpi.top": "Top by {metric}",
        "chatters.kpi.total_messages": "Total messages (filtered)",
        "chatters.chart.ranked": "Chatters by {metric}",
        "chatters.explain.ranked": (
            "The top N chatters ranked by whichever metric is selected above — total "
            "messages or number of distinct channels chatted in."
        ),
        "chatters.explain.correlation": (
            "Each point is a chatter: how many channels they chat in vs. their total "
            "message count, colored by loyalty profile — useful for spotting chatters "
            "that are unusually active for their breadth, or vice versa."
        ),
        "chatters.correlation_heading": "Breadth vs. volume",
        "chatters.correlation_caption": (
            "Each point is a chatter: horizontal position is how many channels they chat "
            "in, vertical position is total messages, colored by loyalty profile."
        ),
        "chatters.chart.correlation": "Channels chatted in vs. total messages",
        "chatters.profile_heading": "Chatter profile",
        "chatters.pick_chatter": "Pick a chatter for a detailed profile",
        "chatters.kpi.channels": "Channels chatted in",
        "chatters.kpi.top_channel_share": "Share of messages in top channel",
        "chatters.kpi.account_age": "Account age",
        "chatters.kpi.regularity": "Message-timing regularity",
        "chatters.regularity_help": (
            "Coefficient of variation of the time between this chatter's messages — a low "
            "value means very regular timing, one bot-likelihood signal among others."
        ),
        "chatters.no_channel_data": "No per-channel activity available yet for this chatter.",
        "chatters.chart.channel_breakdown": "{chatter}'s messages by channel",
        "chatters.explain.channel_breakdown": (
            "How this chatter's messages are split across the channels they chat in."
        ),
        "chatters.anonymize_caption": (
            "⚠️ The table above shows real chatter names, same as elsewhere in the app — "
            "but the downloaded CSV replaces both the chatter id and username with a "
            "one-way pseudonym, so a downloaded file can never be traced back to a real "
            "person."
        ),
        # --- activity ---
        "activity.title": "Stream Activity",
        "activity.description": (
            "How a streamer's activity changed over the event — one segment per "
            "contiguous stretch of the same title and category."
        ),
        "activity.no_streamers": "No streamer data available yet.",
        "activity.pick_streamer": "Pick a streamer",
        "activity.no_data": "No title/category history available yet for this streamer.",
        "activity.filters": "Filters",
        "activity.kpi.segments": "Activity segments",
        "activity.kpi.categories": "Distinct categories",
        "activity.kpi.tracked_duration": "Time tracked",
        "activity.timeline_heading": "Timeline",
        "activity.timeline_caption": (
            "{streamer}'s stream title and category over time — hover a segment for its title."
        ),
        "activity.timeline_row": "Activity",
        "activity.chart.timeline": "Activity timeline",
        "activity.timeline_axis": "time",
        "activity.explain.timeline": (
            "Each colored segment is a stretch of time where the stream's title and "
            "category stayed the same — a new segment starts the moment either one "
            "changes. Hover a segment to see its exact title."
        ),
        "activity.breakdown_heading": "Time per category",
        "activity.chart.breakdown": "{streamer}'s time by category",
        "activity.hours_axis": "hours",
        "activity.explain.breakdown": (
            "Total tracked time this streamer spent in each Twitch category, summed "
            "across every segment (a category can appear more than once in the timeline "
            "above if the streamer returned to it later)."
        ),
    },
    "fr": {
        # --- common ---
        "common.mock_data_banner": (
            "Affichage de **données d'exemple** — connectez une base de données "
            "(`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) pour voir les vrais chiffres."
        ),
        "common.no_data_in_range": "Aucune donnée dans la plage sélectionnée.",
        "common.view_data": "Voir les données sous-jacentes",
        "common.download_csv": "⬇️ Télécharger le CSV",
        "common.how_to_read": "💡 Comment lire ce graphique",
        "period.label": "Période",
        "period.last_hour": "Dernière heure",
        "period.last_6h": "Dernières 6h",
        "period.last_24h": "Dernières 24h",
        "period.all": "Tout l'événement",
        "common.per_hour": "{unit} / heure",
        "common.unit.messages": "messages",
        "common.unit.viewers": "viewers",
        "common.unit.avg_viewers": "viewers moyens",
        "common.unit.channels": "chaînes",
        "common.unit.channel_hours": "heures-chaîne",
        "common.unit.chatters": "chatteurs",
        "common.unit.goals": "objectifs",
        "common.badge.subscriber": "Abonné",
        "common.badge.vip": "VIP",
        "common.badge.moderator": "Modérateur",
        "common.badge.plain_viewer": "Viewer simple",
        "common.chatter_profile.loyal": "Fidèle (une seule chaîne)",
        "common.chatter_profile.multi_streamer": "Multi-streamer",
        "common.chatter_profile.semi_nomad": "Semi-nomade",
        "common.chatter_profile.nomad": "Nomade",
        "common.chatter_profile.caption": (
            "Les chatteurs fidèles ne discutent que dans une seule chaîne ; les nomades "
            "répartissent leurs messages sur de nombreuses chaînes pendant l'événement."
        ),
        # --- recherche globale (barre latérale, chaque page) ---
        "search.label": "🔍 Rechercher",
        "search.placeholder": "Streamers, catégories, titres, emotes, chatteurs...",
        "search.no_results": "Aucun résultat pour « {query} ».",
        "search.more_results": "+{count} de plus — affinez votre recherche pour réduire la liste.",
        "search.type.streamer": "Streamer",
        "search.type.category": "Catégorie",
        "search.type.title": "Titre de stream",
        "search.type.emote": "Emote",
        "search.type.chatter": "Chatteur",
        # --- titres de page (utilisés dans l'en-tête de page et les cartes de l'accueil) ---
        "donations.title": "Dons",
        "streamers.title": "Streamers",
        "games.title": "Jeux",
        "goals.title": "Objectifs de dons",
        "chat.title": "Chat en direct",
        "community.title": "Communauté",
        "tracker.title": "Suivi des dons",
        # --- home ---
        "home.title": "ZEvent Dataviz",
        "home.tagline": "Tableaux de bord de modélisation de données pour le marathon caritatif ZEvent.",
        "home.db_error": (
            "Les identifiants de la base sont configurés mais la connexion a échoué. "
            "Vérifiez `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` et l'accès réseau."
        ),
        "home.about_body": (
            "Cette application diffuse et analyse en direct les données de la dernière "
            "édition du ZEvent (**3-6 septembre 2026**) — un marathon caritatif de jeu "
            "vidéo français où des streamers collectent des dons pour une cause. Elle "
            "couvre quatre domaines de données directement depuis l'entrepôt, au fil de "
            "l'événement : les **dons**, les **streamers**, le **chat en direct**, et les "
            "**chatteurs**.\n\n"
            "Elle est en lecture seule et se connecte à un entrepôt PostgreSQL partagé "
            "(via PgBouncer) modélisé avec dbt à travers les schémas `raw` → `stg` → "
            "`int` → `marts`, alimenté par deux pipelines indépendants : le site de dons/"
            "objectifs du ZEvent lui-même, et les métadonnées de stream/chat de Twitch."
        ),
        "home.kpi_heading": "Aperçu de l'événement",
        "home.kpi.duration": "Durée de suivi des dons",
        "home.kpi.duration_value": "{hours} h",
        "home.kpi.streamers": "Streamers",
        "home.kpi.chatters": "Chatteurs",
        "home.kpi.messages": "Messages de chat",
        "home.kpi.peak_viewers": "Pic de viewers simultanés",
        "home.pages_heading": "Pages",
        "home.related_projects": (
            "**Projets liés** — cette application fait partie d'un petit écosystème : "
            "`zevent-analysis` (analyse hors-ligne plus poussée), `zevent-db` (l'entrepôt "
            "que cette application lit), et `zevent-infra-monitoring` (supervision du "
            "pipeline/de l'infrastructure). Ce tableau de bord est actuellement le seul "
            "des quatre à avoir un livrable fonctionnel."
        ),
        # --- donations ---
        "donations.description": (
            "Dons cumulés sur la durée de l'événement, évolution du rythme heure par "
            "heure, et mouvements du classement."
        ),
        "donations.no_data": "Aucune donnée de dons disponible pour le moment.",
        "donations.filters": "Filtres",
        "donations.kpi.total_raised": "Total collecté",
        "donations.kpi.active_streamers": "Streamers actifs (dernière heure)",
        "donations.kpi.best_hour": "Meilleure heure",
        "donations.chart.cumulative": "Dons cumulés",
        "donations.chart.pace": "Rythme des dons (par heure)",
        "donations.phases_heading": "Phases de l'événement",
        "donations.chart.by_phase": "Dons par phase de l'événement",
        "donations.phases_caption": (
            "L'événement est découpé en trois phases (ouverture, milieu, sprint final). "
            "Ce graphique se remplit au fur et à mesure que l'événement les traverse réellement."
        ),
        "donations.movers_heading": "Mouvements du classement",
        "donations.movers_caption": (
            "Streamers avec les plus grosses variations récentes de rang de dons "
            "(à la hausse ou à la baisse)."
        ),
        "donations.quality_heading": "Qualité des données",
        "donations.quality_no_data": "Aucune donnée de réconciliation disponible pour le moment.",
        "donations.quality_ok": "Totaux de dons réconciliés (Δ = {divergence} €) au {time}.",
        "donations.quality_bad": "Les totaux de dons divergent de {divergence} € au {time}.",
        "donations.quality_caption": (
            "Ceci compare le total de dons de l'événement à la somme des totaux "
            "individuels par streamer sur le même instantané — un contrôle basique "
            "d'intégrité des données."
        ),
        "donations.explain.cumulative": (
            "Le total cumulé des dons de tous les streamers, depuis le début de "
            "l'événement jusqu'à maintenant. Toujours stable ou croissant — jamais à la baisse."
        ),
        "donations.explain.pace": (
            "Ce qui a été collecté durant chaque heure individuelle (pas cumulé). Les pics "
            "correspondent généralement à des incitations, des paliers, ou un streamer "
            "populaire qui passe en direct."
        ),
        "donations.explain.phase": (
            "Les dons regroupés selon les trois phases de l'événement (ouverture, milieu, "
            "sprint final), pour voir quelle période a le plus rapporté."
        ),
        "donations.by_activity_heading": "Dons par activité",
        "donations.no_activity_data": "Aucune donnée de dons attribués à une activité pour le moment.",
        "donations.by_activity_caption": (
            "Les dons de chaque heure attribués à la catégorie Twitch diffusée par une "
            "chaîne cette heure-là — une approximation à la granularité de l'heure, comme "
            "le classement des titres de stream sur la page Jeux."
        ),
        "donations.chart.by_activity": "Dons par catégorie Twitch",
        "donations.explain.by_activity": (
            "Pendant quelles activités (catégories Twitch) les dons ont été collectés — "
            "utile pour repérer si un jeu ou un segment particulier (par exemple un défi "
            "caritatif) a généré disproportionnellement plus de dons."
        ),
        # --- streamers ---
        "streamers.description": (
            "Qui a récolté combien, avec l'audience, l'engagement, et un profil détaillé par streamer."
        ),
        "streamers.no_data": "Aucune donnée de streamer disponible pour le moment.",
        "streamers.filters": "Filtres",
        "streamers.search": "Rechercher par nom",
        "streamers.category_filter": "Filtrer par catégorie principale",
        "streamers.min_viewers": "Viewers moyens minimum",
        "streamers.rank_by": "Classer les streamers par",
        "streamers.rank.donations": "Dons",
        "streamers.rank.engagement": "Engagement chat (messages)",
        "streamers.rank.audience": "Audience (viewers moyens)",
        "streamers.top_n": "Afficher le top N",
        "streamers.kpi.top": "Premier par {metric}",
        "streamers.kpi.total_raised": "Total collecté (affiché)",
        "streamers.kpi.total_messages": "Total messages chat (affiché)",
        "streamers.chart.ranked": "Streamers par {metric}",
        "streamers.correlation_heading": "Audience vs. engagement",
        "streamers.correlation_caption": (
            "Chaque point est un streamer — la taille de la bulle représente les dons "
            "collectés. Utile pour repérer les cas atypiques (forte audience / peu de chat, ou l'inverse)."
        ),
        "streamers.chart.correlation": "Viewers moyens vs. messages du chat",
        "streamers.profile_heading": "Profil du streamer",
        "streamers.pick_streamer": "Choisir un streamer pour un profil détaillé",
        "streamers.kpi.peak_viewers": "Pic de viewers",
        "streamers.kpi.uptime": "Temps de live",
        "streamers.kpi.top_category": "Catégorie principale",
        "streamers.kpi.unique_chatters": "Chatteurs uniques",
        "streamers.uptime_quirk": "100%+ (anomalie de données)",
        "streamers.chart.loyalty_mix": "Mix de fidélité des chatteurs de {streamer}",
        "streamers.no_diurnal_data": "Aucun profil horaire de viewers disponible pour ce streamer.",
        "streamers.chart.diurnal": "Profil horaire de viewers vs. moyenne de l'événement",
        "streamers.hour_of_day": "heure de la journée (Europe/Paris)",
        "streamers.event_average": "Moyenne de l'événement",
        "streamers.explain.ranked": (
            "Le top N des streamers classés selon la métrique choisie ci-dessus — dons, "
            "messages du chat, ou viewers moyens. Une barre par streamer, la plus longue en premier."
        ),
        "streamers.explain.correlation": (
            "Chaque point est un streamer : la position horizontale est les viewers "
            "moyens, la verticale les messages du chat, et la taille de la bulle les dons "
            "collectés. Un point isolé des autres mérite un coup d'œil — par exemple "
            "beaucoup de viewers mais un chat silencieux."
        ),
        "streamers.explain.loyalty_mix": (
            "Combien des chatteurs de ce streamer ne discutent que chez lui (fidèles) "
            "contre ceux qui discutent aussi sur d'autres chaînes pendant l'événement "
            "(multi-streamer, semi-nomade, nomade)."
        ),
        "streamers.explain.diurnal": (
            "Viewers moyens par heure de la journée pour ce streamer (ligne pleine) vs. "
            "la moyenne de l'événement (pointillés) — montre si les heures de pointe de ce "
            "streamer correspondent à celles des autres, ou en diffèrent."
        ),
        # --- games ---
        "games.description": (
            "Quelles catégories sont jouées, l'audience simultanée dans le temps, et les sessions récentes."
        ),
        "games.filters": "Filtres",
        "games.kpi.concurrent_now": "Viewers simultanés actuels",
        "games.kpi.channels_now": "Chaînes en direct actuellement",
        "games.kpi.peak_concurrent": "Pic de viewers simultanés",
        "games.chart.viewership": "Audience simultanée de l'événement",
        "games.chart.live_channels": "Chaînes en direct dans le temps",
        "games.no_viewership": "Aucune donnée d'audience disponible pour le moment.",
        "games.categories_heading": "Catégories",
        "games.category_filter": "Filtrer les catégories",
        "games.chart.by_category": "Heures-chaîne par catégorie",
        "games.no_categories": "Aucune donnée de catégorie disponible pour le moment.",
        "games.sessions_heading": "Sessions de stream récentes",
        "games.no_sessions": "Aucune session de stream enregistrée pour le moment.",
        "games.titles_heading": "Classement des titres de stream",
        "games.no_titles": "Aucune donnée de titre de stream disponible pour le moment.",
        "games.titles_caption": (
            "Messages et dons attribués à chaque titre en faisant correspondre chaîne + "
            "heure — une approximation à la granularité de l'heure, car un changement de "
            "titre en milieu d'heure répartirait l'activité de cette heure entre plusieurs titres."
        ),
        "games.titles_rank_by": "Classer les titres par",
        "games.titles_by_messages": "Messages",
        "games.titles_by_donations": "Dons",
        "games.chart.titles": "Meilleurs titres de stream",
        "games.explain.viewership": (
            "Total des viewers simultanés sur toutes les chaînes en direct, dans le temps "
            "— un indicateur de l'audience globale de l'événement à un instant donné."
        ),
        "games.explain.live_channels": (
            "Combien de chaînes étaient en direct simultanément, heure par heure."
        ),
        "games.explain.by_category": (
            "Total d'heures-chaîne passées sur chaque catégorie — une catégorie jouée par "
            "de nombreuses chaînes brièvement peut dépasser une jouée par peu de chaînes longtemps."
        ),
        "games.explain.titles": (
            "Titres de stream classés par messages ou par dons (au choix ci-dessus) — une "
            "approximation à la granularité de l'heure des moments les plus actifs."
        ),
        # --- goals ---
        "goals.description": (
            "Les objectifs de dons fixés par les streamers — par catégorie et par streamer."
        ),
        "goals.no_data": "Aucune donnée d'objectif de don disponible pour le moment.",
        "goals.caveat": (
            "⚠️ Les montants des objectifs sont choisis par les streamers et souvent "
            "volontairement absurdes (des blagues à plusieurs centaines de millions "
            "d'euros existent). Cette page affiche des **comptages**, pas des sommes en "
            "euros, pour qu'une poignée d'objectifs blagueurs ne fausse pas le tableau."
        ),
        "goals.kpi.total_goals": "Total des objectifs",
        "goals.kpi.categories": "Catégories",
        "goals.kpi.streamers": "Streamers participants",
        "goals.category_heading": "Objectifs par catégorie",
        "goals.chart.by_category": "Objectifs par catégorie",
        "goals.chart.top_setters": "Streamers avec le plus d'objectifs fixés",
        "goals.distribution_heading": "Explorer la distribution des montants",
        "goals.no_amounts": "Aucune donnée de montant disponible pour le moment.",
        "goals.distribution_caption": (
            "Montants bruts des objectifs, à l'échelle logarithmique — la queue de "
            "droite est presque entièrement composée de blagues. Choisissez votre "
            "propre seuil plutôt que de faire confiance à une valeur fixe."
        ),
        "goals.cutoff_slider": "Considérer les objectifs sous ce montant comme « réalistes »",
        "goals.chart.distribution": "Distribution des montants d'objectifs (échelle log)",
        "goals.log_amount_axis": "log₁₀(montant en €)",
        "goals.kpi.below_cutoff": "Sous le seuil",
        "goals.kpi.above_cutoff": "Au-dessus du seuil (probables blagues)",
        "goals.cutoff_caption": "Déplacez le curseur ci-dessus pour changer ce qui compte comme « réaliste ».",
        "goals.explain.by_category": (
            "Combien d'objectifs les streamers ont fixés dans chaque catégorie (récurrent, "
            "seuil sur don unique, etc.) — des comptages, pas des sommes, pour que les "
            "montants blagueurs ne dominent pas."
        ),
        "goals.explain.top_setters": (
            "Les streamers qui ont fixé le plus d'objectifs de dons, quel que soit le montant."
        ),
        "goals.explain.distribution": (
            "Le montant brut de chaque objectif de type 'donation', à l'échelle "
            "logarithmique pour que les montants réalistes et blagueurs tiennent sur un "
            "même axe. La ligne pointillée marque le seuil choisi ci-dessus."
        ),
        # --- chat ---
        "chat.description": (
            "Volume de messages dans le temps, les chaînes les plus actives, et les emotes les plus utilisées."
        ),
        "chat.no_data": "Aucune donnée de chat disponible pour le moment.",
        "chat.filters": "Filtres",
        "chat.kpi.messages_this_hour": "Messages cette heure",
        "chat.kpi.chatters_this_hour": "Chatteurs uniques cette heure",
        "chat.kpi.total_messages": "Total messages (événement)",
        "chat.chart.activity": "Messages du chat par heure (toutes chaînes)",
        "chat.engagement_heading": "Taux d'engagement du chat",
        "chat.engagement_caption": (
            "Messages par minute pour 100 viewers — un indicateur d'engouement/engagement "
            "qui tient compte de la taille de l'audience. Il n'y a aucune donnée de "
            "sentiment/émotion dans l'entrepôt, donc c'est le signal réel le plus proche de "
            "« à quel point le chat est enthousiaste en ce moment »."
        ),
        "chat.no_engagement": "Aucune donnée de taux d'engagement disponible pour le moment (nécessite viewers > 0).",
        "chat.chart.engagement": "Taux d'engagement du chat dans le temps",
        "chat.engagement_axis": "messages / min / 100 viewers",
        "chat.heatmap_heading": "Carte de chaleur de l'activité",
        "chat.no_heatmap": "Aucune donnée de chat par chaîne disponible pour le moment.",
        "chat.channel_filter": "Filtrer les chaînes",
        "chat.heatmap_caption": "Plus foncé = plus de messages sur cette chaîne, à cette heure.",
        "chat.chart.heatmap": "Messages par chaîne et par heure",
        "chat.channels_heading": "Chaînes les plus actives",
        "chat.no_channels": "Aucune donnée de chat par chaîne disponible pour le moment.",
        "chat.channels_caption": (
            "Composition des messages par badge — une chaîne avec une forte part "
            "d'abonnés/modérateurs a une communauté plus établie que ce que le volume "
            "brut montre à lui seul."
        ),
        "chat.chart.composition": "Composition des messages par chaîne",
        "chat.emotes_heading": "Emotes les plus utilisées",
        "chat.no_emotes": "Aucune donnée d'emote disponible pour le moment.",
        "chat.emotes_unnamed_caveat": (
            "⚠️ Le catalogue d'emotes n'est pas encore alimenté pour cet événement, les emotes "
            "sont donc affichées avec un identifiant brut raccourci plutôt que leur nom — cela "
            "se remplira automatiquement une fois le catalogue disponible."
        ),
        "chat.uses_axis": "utilisations",
        "chat.explain.activity": (
            "Total des messages du chat par heure, toutes chaînes confondues — un aperçu "
            "rapide des moments où l'activité globale du chat a été la plus forte."
        ),
        "chat.explain.engagement": (
            "Messages par minute pour 100 viewers, moyenné sur toutes les chaînes — ceci "
            "tient compte de la taille de l'audience, pour qu'une petite chaîne au chat "
            "très actif ne soit pas éclipsée par le volume brut d'une grande chaîne."
        ),
        "chat.explain.heatmap": (
            "Une cellule par chaîne x heure ; plus foncé signifie plus de messages. Utile "
            "pour repérer d'un coup d'œil quelles chaînes étaient actives à quel moment."
        ),
        "chat.explain.composition": (
            "Les messages de chaque chaîne répartis selon qui les a envoyés (abonné, VIP, "
            "modérateur, viewer simple) — une forte part d'abonnés/modérateurs suggère une "
            "communauté établie, pas seulement du volume brut."
        ),
        "chat.explain.emotes": (
            "Les emotes les plus utilisées de l'événement, par nombre d'utilisations. Les "
            "emotes absentes du catalogue sont affichées avec un identifiant raccourci "
            "plutôt que leur vrai nom (voir la note au-dessus du graphique, le cas échéant)."
        ),
        # --- community ---
        "community.description": (
            "Qui discute, leur fidélité à une seule chaîne, et quelles chaînes partagent une audience."
        ),
        "community.no_data": "Aucune donnée de chatteur disponible pour le moment.",
        "community.kpi.total_chatters": "Total chatteurs",
        "community.kpi.multi_channel": "Chatteurs multi-chaînes",
        "community.kpi.loyal_share": "Part fidèle à une seule chaîne",
        "community.growth_heading": "Croissance des chatteurs",
        "community.growth_caption": "Chatteurs distincts cumulés vus, dans le temps.",
        "community.chart.growth": "Chatteurs cumulés dans le temps",
        "community.cumulative_chatters": "chatteurs cumulés",
        "community.hourly_network_heading": "Communauté de chatteurs, heure par heure",
        "community.hourly_network_caption": (
            "Chaque lien signifie que deux chaînes partagent des chatteurs cette heure-là — "
            "plus épais/foncé signifie plus de chatteurs partagés. Choisissez une heure pour "
            "voir l'évolution du réseau communautaire."
        ),
        "community.hour_picker": "Heure",
        "community.no_hourly_network": "Aucune donnée de réseau horaire disponible pour le moment.",
        "community.chart.hourly_network": "Réseau d'audience partagée à {hour}",
        "community.chart.loyalty_mix": "Mix de fidélité des chatteurs",
        "community.chart.account_age": "Chatteurs par ancienneté du compte Twitch",
        "community.age.new": "Nouveau (<30j)",
        "community.age.month_to_year": "1 mois - 1 an",
        "community.age.one_to_three": "1 - 3 ans",
        "community.age.three_plus": "3 ans et plus",
        "community.age.unknown": "Inconnu",
        "community.age_caption": (
            "L'ancienneté du compte est inconnue pour les chatteurs dont le profil "
            "n'a pas pu être récupéré."
        ),
        "community.chatters_heading": "Chatteurs les plus actifs",
        "community.no_chatters": "Aucun classement de chatteurs disponible pour le moment.",
        "community.chatters_caption": (
            "Certains « meilleurs chatteurs » sont des bots (ex. bots de modération) "
            "plutôt que des personnes — la chaîne est affichée à côté pour que ce soit "
            "visible sans deviner."
        ),
        "community.channel_filter": "Filtrer par chaîne",
        "community.hide_bots": "Masquer les bots probables",
        "community.top_n": "Afficher le top N",
        "community.chart.top_chatters": "Meilleurs chatteurs par nombre de messages",
        "community.network_heading": "Audiences partagées entre chaînes",
        "community.no_network": "Aucun chevauchement d'audience détecté pour le moment.",
        "community.network_caption": (
            "Chaque paire de chaînes qui partage des chatteurs, sous forme de graphe "
            "réseau — plus les liens sont épais/foncés, plus de chatteurs sont partagés, "
            "et chaque chaîne garde sa propre couleur fixe, comme le graphe heure par heure ci-dessus."
        ),
        "community.chart.network": "Réseau d'audiences partagées",
        "community.explain.growth": (
            "Le nombre cumulé de chatteurs distincts vus jusqu'à présent, dans le temps — "
            "toujours stable ou croissant."
        ),
        "community.explain.hourly_network": (
            "Un nœud par chaîne, un lien par paire de chaînes ayant partagé des chatteurs "
            "cette heure-là — plus le lien est épais/foncé, plus de chatteurs sont "
            "partagés. Chaque nœud a sa propre couleur fixe, pour repérer facilement une "
            "même chaîne d'une heure à l'autre."
        ),
        "community.explain.loyalty_mix": (
            "Combien de chatteurs ne discutent que dans une seule chaîne (fidèles) contre "
            "ceux qui répartissent leurs messages sur plusieurs (multi-streamer, "
            "semi-nomade, nomade)."
        ),
        "community.explain.account_age": (
            "Les chatteurs répartis selon l'âge de leur compte Twitch — un compte très "
            "récent n'est pas forcément un bot, mais un pic de comptes tout neufs peut "
            "mériter un coup d'œil."
        ),
        "community.explain.top_chatters": (
            "Les chatteurs les plus actifs par nombre de messages. Certains « top "
            "chatteurs » sont des bots de modération plutôt que des personnes — utilisez "
            "« Masquer les bots probables » pour voir uniquement les vrais viewers, ou la "
            "colonne chaîne pour les repérer vous-même."
        ),
        "community.explain.network": (
            "Un nœud par chaîne, dont la taille reflète avec combien d'autres chaînes elle "
            "partage une audience ; un lien par paire de chaînes, plus épais/foncé pour "
            "plus de chatteurs partagés. À l'échelle de l'événement, contrairement au "
            "graphe heure par heure ci-dessus."
        ),
        # --- tracker ---
        "tracker.description": (
            "Suivre les objectifs de dons d'un streamer : quand chacun a commencé, "
            "quand il a été atteint, et combien de temps cela a pris."
        ),
        "tracker.global_heading": "Vue d'ensemble globale",
        "tracker.no_global_data": "Aucun objectif de don suivable, tous streamers confondus, pour le moment.",
        "tracker.global_caption": (
            "Progression de complétion des objectifs sur tous les streamers ayant des "
            "objectifs de type « donation »."
        ),
        "tracker.chart.top_completers": "Streamers avec le plus d'objectifs atteints",
        "tracker.per_streamer_heading": "Par streamer",
        "tracker.no_streamers": "Aucune donnée de streamer disponible pour le moment.",
        "tracker.pick_streamer": "Choisir un streamer",
        "tracker.no_goals": "Aucun objectif de don suivable pour ce streamer pour le moment.",
        "tracker.kpi.total": "Objectifs suivis",
        "tracker.kpi.done": "Atteints",
        "tracker.kpi.in_progress": "En cours",
        "tracker.kpi.not_started": "Pas commencés",
        "tracker.status.done": "✅ Atteint",
        "tracker.status.in_progress": "🟡 En cours",
        "tracker.status.not_started": "⚪ Pas commencé",
        "tracker.view_picker": "Vue",
        "tracker.view.timeline": "Chronologie",
        "tracker.view.duration_bar": "Temps pour atteindre",
        "tracker.timeline_caption": (
            "Un objectif commence quand le total des dons de {streamer} a atteint le "
            "montant de l'objectif précédent, et se termine quand il atteint son propre montant."
        ),
        "tracker.chart.timeline": "Chronologie des objectifs",
        "tracker.timeline_axis": "temps",
        "tracker.no_timeline": "Aucun objectif n'a encore commencé pour ce streamer.",
        "tracker.duration_bar_caption": "Le temps qu'a pris chaque objectif atteint, classé.",
        "tracker.no_completed_goals": "Aucun objectif atteint pour le moment pour ce streamer.",
        "tracker.chart.duration_bar": "Temps pour atteindre chaque objectif",
        "tracker.duration_axis": "heures",
        "tracker.table_heading": "Tous les objectifs",
        "tracker.table_caption": "Chaque objectif, avec la durée exacte en heures et en secondes.",
        "tracker.column.goal": "Objectif",
        "tracker.column.amount": "Montant",
        "tracker.column.status": "Statut",
        "tracker.column.started": "Commencé",
        "tracker.column.completed": "Terminé",
        "tracker.column.duration": "Durée",
        "tracker.column.duration_hours": "Durée (heures)",
        "tracker.column.duration_seconds": "Durée (secondes)",
        "tracker.explain.top_completers": (
            "Les streamers ayant terminé le plus d'objectifs de dons jusqu'à présent, classés."
        ),
        "tracker.explain.timeline": (
            "Chaque barre s'étend du démarrage d'un objectif (fin du précédent) jusqu'à sa "
            "réalisation, ou jusqu'à maintenant s'il est encore en cours. Les barres d'un "
            "même streamer ne se chevauchent jamais dans le temps, puisqu'un objectif "
            "démarre où le précédent s'est terminé."
        ),
        "tracker.explain.duration_bar": (
            "Le temps qu'a pris chaque objectif terminé, du démarrage à la réalisation, "
            "classé du plus long au plus court."
        ),
        # --- chatters ---
        "chatters.title": "Chatteurs",
        "chatters.description": (
            "Analyses par chatteur : fidélité, activité, et profil détaillé — comme la "
            "page Streamers, mais pour les chatteurs individuels."
        ),
        "chatters.no_data": "Aucune donnée de chatteur disponible pour le moment.",
        "chatters.filters": "Filtres",
        "chatters.search": "Rechercher par nom",
        "chatters.profile_filter": "Filtrer par profil de fidélité",
        "chatters.age_filter": "Filtrer par âge du compte",
        "chatters.min_messages": "Messages minimum",
        "chatters.hide_bots": "Masquer les bots probables",
        "chatters.rank_by": "Classer les chatteurs par",
        "chatters.rank.messages": "Messages",
        "chatters.rank.channels": "Chaînes fréquentées",
        "chatters.top_n": "Afficher le top N",
        "chatters.kpi.total": "Chatteurs (filtrés)",
        "chatters.kpi.top": "Premier par {metric}",
        "chatters.kpi.total_messages": "Total messages (filtrés)",
        "chatters.chart.ranked": "Chatteurs par {metric}",
        "chatters.explain.ranked": (
            "Le top N des chatteurs classés selon la métrique choisie ci-dessus — total "
            "des messages ou nombre de chaînes distinctes fréquentées."
        ),
        "chatters.explain.correlation": (
            "Chaque point est un chatteur : le nombre de chaînes fréquentées contre son "
            "total de messages, coloré par profil de fidélité — utile pour repérer les "
            "chatteurs anormalement actifs pour leur diversité, ou l'inverse."
        ),
        "chatters.correlation_heading": "Diversité vs. volume",
        "chatters.correlation_caption": (
            "Chaque point est un chatteur : la position horizontale est le nombre de "
            "chaînes fréquentées, la verticale le total des messages, coloré par profil de fidélité."
        ),
        "chatters.chart.correlation": "Chaînes fréquentées vs. total des messages",
        "chatters.profile_heading": "Profil du chatteur",
        "chatters.pick_chatter": "Choisir un chatteur pour un profil détaillé",
        "chatters.kpi.channels": "Chaînes fréquentées",
        "chatters.kpi.top_channel_share": "Part des messages sur la chaîne principale",
        "chatters.kpi.account_age": "Âge du compte",
        "chatters.kpi.regularity": "Régularité du rythme des messages",
        "chatters.regularity_help": (
            "Coefficient de variation du temps entre les messages de ce chatteur — une "
            "valeur basse signifie un rythme très régulier, un signal parmi d'autres de "
            "probabilité de bot."
        ),
        "chatters.no_channel_data": "Aucune activité par chaîne disponible pour ce chatteur.",
        "chatters.chart.channel_breakdown": "Messages de {chatter} par chaîne",
        "chatters.explain.channel_breakdown": (
            "Comment les messages de ce chatteur se répartissent entre les chaînes qu'il fréquente."
        ),
        "chatters.anonymize_caption": (
            "⚠️ Le tableau ci-dessus affiche les vrais noms des chatteurs, comme ailleurs "
            "dans l'application — mais le CSV téléchargé remplace à la fois l'identifiant "
            "et le nom d'utilisateur par un pseudonyme à sens unique, pour qu'un fichier "
            "téléchargé ne puisse jamais être retracé jusqu'à une personne réelle."
        ),
        # --- activity ---
        "activity.title": "Activité de stream",
        "activity.description": (
            "Comment l'activité d'un streamer a évolué pendant l'événement — un segment "
            "par plage continue du même titre et de la même catégorie."
        ),
        "activity.no_streamers": "Aucune donnée de streamer disponible pour le moment.",
        "activity.pick_streamer": "Choisir un streamer",
        "activity.no_data": "Aucun historique de titre/catégorie disponible pour ce streamer.",
        "activity.filters": "Filtres",
        "activity.kpi.segments": "Segments d'activité",
        "activity.kpi.categories": "Catégories distinctes",
        "activity.kpi.tracked_duration": "Durée suivie",
        "activity.timeline_heading": "Chronologie",
        "activity.timeline_caption": (
            "Le titre et la catégorie du stream de {streamer} dans le temps — survolez un "
            "segment pour voir son titre."
        ),
        "activity.timeline_row": "Activité",
        "activity.chart.timeline": "Chronologie d'activité",
        "activity.timeline_axis": "temps",
        "activity.explain.timeline": (
            "Chaque segment coloré est une plage de temps où le titre et la catégorie du "
            "stream sont restés identiques — un nouveau segment démarre dès que l'un des "
            "deux change. Survolez un segment pour voir son titre exact."
        ),
        "activity.breakdown_heading": "Temps par catégorie",
        "activity.chart.breakdown": "Temps de {streamer} par catégorie",
        "activity.hours_axis": "heures",
        "activity.explain.breakdown": (
            "Temps total suivi que ce streamer a passé dans chaque catégorie Twitch, "
            "cumulé sur tous les segments (une catégorie peut apparaître plusieurs fois "
            "dans la chronologie ci-dessus si le streamer y est revenu plus tard)."
        ),
    },
}
