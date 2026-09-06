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
        "common.footer": (
            "ZEvent Dataviz v{version} — an unofficial fan dashboard for the "
            "[ZEvent](https://zevent.fr) charity marathon, not affiliated with the event or "
            "its organizers."
        ),
        "common.no_data_in_range": "No data in the selected range.",
        "common.view_data": "View underlying data",
        "common.download_csv": "⬇️ Download CSV",
        "common.prev_page": "⬅️ Previous",
        "common.next_page": "Next ➡️",
        "common.page_of": "Page {page} of {pages}",
        "common.pie_other": "Other",
        "common.how_to_read": "💡 How to read this chart",
        "common.date_filter_caveat": (
            "This section reflects the whole event, not the sidebar date filter — "
            "it's pre-aggregated with no per-row timestamp to filter by."
        ),
        "common.entity_filter_caveat": (
            "This section isn't narrowed by the sidebar's streamer/chatter filters either — "
            "it's pre-aggregated with no per-row channel/chatter to filter by."
        ),
        "filter.date_range_label": "📅 Date range",
        "filter.streamer_label": "🎙️ Streamers",
        "filter.chatter_label": "🗣️ Chatters",
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
        # --- nav ---
        "nav.info_section": "Info",
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
            "raise donations for a cause. It's read-only, updated straight from the "
            "warehouse as the event happens."
        ),
        "home.about_link": "How this dashboard works, and where its data comes from",
        "home.kpi_heading": "Event snapshot",
        "home.kpi.total_raised": "Total raised",
        "home.kpi.duration": "Donation tracking span",
        "home.kpi.duration_value": "{hours} h",
        "home.kpi.streamers": "Streamers",
        "home.kpi.chatters": "Chatters",
        "home.kpi.messages": "Chat messages",
        "home.kpi.peak_viewers": "Peak concurrent viewers",
        "home.tech_expander_label": "🔧 Database internals (for data engineers)",
        "home.tech_caption": (
            "The warehouse behind every page on this site: how many tables exist "
            "in each dbt layer, how many rows and how much disk space they hold, "
            "and how data flows from raw ingestion to the marts every page reads "
            "from. Collapsed by default — this is data-engineering detail, not "
            "something every visitor needs."
        ),
        "home.tech_no_data": (
            "This section reflects the real database's own catalog metadata and "
            "isn't available with mock/demo data."
        ),
        "home.tech_kpi.tables": "Tables & views",
        "home.tech_kpi.rows": "Total rows (estimate)",
        "home.tech_kpi.size": "Total size on disk",
        "home.tech_chart.lineage": "Data lineage: dbt layers, by table count",
        "home.tech_stage.raw": "raw",
        "home.tech_stage.stg": "stg (staging)",
        "home.tech_stage.int": "int (intermediate)",
        "home.tech_stage.marts": "marts",
        "home.tech_stage.pages": "this app's 14 pages",
        "home.explain.tech_lineage": (
            "dbt's own layering, not a per-table dependency graph — Postgres "
            "doesn't retain the SQL that built a materialized table once it's "
            "built, so a *table*-level lineage arrow (\"this mart reads exactly "
            "these 3 int models\") isn't something this page can honestly "
            "derive from the database alone; that level of detail lives in the "
            "dbt project's own `manifest.json`, not this app's own read-only "
            "connection to the warehouse it built. What *is* real: `raw` "
            "holds untouched ingested data; `stg` normalizes it into a "
            "consistent shape without changing its meaning; `int` builds "
            "per-chatter/per-channel/per-hour aggregates from staging; `marts` "
            "are the query-ready tables every page actually reads from (see "
            "`app/data/repository.py::PostgresDataSource` for exactly which "
            "mart backs which chart). Flow width is each stage's real table "
            "count, from the query below. For the real per-model lineage "
            "graph, see dbt's own generated docs below, if hosted."
        ),
        "home.tech_dbt_docs_button": "📖 Open dbt docs (real per-model lineage)",
        "home.tech_dbt_docs_hint": (
            "No `dbt docs` build is linked yet. Run `dbt docs generate` in the "
            "warehouse project, host the output (even a plain static file "
            "server works), and set `DBT_DOCS_URL` in this app's `.env` to "
            "show a link to it here."
        ),
        "home.tech_table.column.schema": "Schema",
        "home.tech_table.column.table": "Table",
        "home.tech_table.column.kind": "Kind",
        "home.tech_table.column.rows": "Rows (est.)",
        "home.tech_table.column.size": "Size",
        "home.tech_table.kind.table": "table",
        "home.tech_table.kind.view": "view",
        "home.daily_heading": "Daily trend",
        "home.daily_caption": "Event-wide totals bucketed by day.",
        "home.chart.daily": "Donations per day",
        "home.explain.daily": (
            "One bar per calendar day of the event — a coarser view than the hourly "
            "charts on other pages, useful for spotting which day raised the most."
        ),
        "home.pages_heading": "Pages",
        # --- donations ---
        "donations.description": (
            "Cumulative donations over the course of the event, how the pace evolves hour "
            "by hour, and who's moving on the leaderboard."
        ),
        "donations.no_data": "No donation data available yet.",
        "donations.kpi.total_raised": "Total raised",
        "donations.kpi.active_streamers": "Active streamers (last hour)",
        "donations.kpi.best_hour": "Best hour",
        "donations.podium_heading": "Top fundraisers",
        "donations.podium_caption": "The 3 streamers who've raised the most so far.",
        "donations.chart.podium": "Top 3 by donations raised",
        "donations.explain.podium": (
            "Total donations raised per streamer, event-wide (not affected by the sidebar "
            "date filter) — bar height is the real amount, ranked 1st/2nd/3rd."
        ),
        "donations.chart.cumulative": "Cumulative donations",
        "donations.chart.pace": "Donation pace (per hour)",
        "donations.donation_race_heading": "Donation leaderboard, hour by hour",
        "donations.no_donation_race": "No per-channel donation ranking available yet.",
        "donations.donation_race_top_n": "Show top N streamers",
        "donations.donation_race_caption": (
            "The top streamers overall by cumulative donations, hour by hour — each "
            "streamer's full history in the window, not just the hours they led."
        ),
        "donations.chart.donation_race": "Top streamers by donations, over time",
        "donations.explain.donation_race": (
            "One line per streamer among the top N overall by cumulative donations; "
            "hover a point for its exact rank that hour among every streamer. Unlike "
            "the event-wide cumulative total above, this shows which specific "
            "streamers were leading, and how that changed."
        ),
        "donations.spikes_heading": "Notable spikes",
        "donations.no_spikes": "No standout donation moments in this range yet.",
        "donations.spikes_caption": "The single biggest donation moments, with what was on screen at the time.",
        "donations.explain.spikes": (
            "Each row is one unusually large donation — its title/category and how "
            "busy chat was that hour, for context on what might have driven it."
        ),
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
        "donations.editions_heading": "This year vs. previous editions",
        "donations.editions_caption": (
            "Cumulative donations aligned by hours since each edition started, not by "
            "calendar date, so the shapes compare directly. This event's own curve comes "
            "from this app's data; past editions' curves are read from "
            "[EvenMoreStats](https://zevent.gdoc.fr) (evenmorestats.fr), an unofficial "
            "third-party ZEvent tracker — not this app's own warehouse."
        ),
        "donations.editions_unavailable": (
            "Previous-edition comparison is temporarily unavailable — couldn't reach the "
            "external data source (EvenMoreStats)."
        ),
        "donations.chart.editions": "Cumulative donations by hours since start",
        "donations.hours_since_start": "hours since event start",
        "donations.editions_y_axis": "€ (log scale)",
        "donations.explain.editions": (
            "Each year gets its own color; this year's line is drawn thicker, but every "
            "edition — including this one — starts its own clock at hour 0, so a steeper "
            "early climb or an earlier finish-line crossing shows up directly as one curve "
            "pulling ahead of another. The y-axis is logarithmic (each gridline is 10x the "
            "last) so a past edition with a much higher final total doesn't flatten every "
            "other curve, including this year's own, into the bottom of the chart."
        ),
        "donations.day_evolution_heading": "Day-by-day evolution, across editions",
        "donations.day_evolution_caption": (
            "Each \"day\" is a fixed 24-hour window from kickoff (hour 0-24, 24-48, "
            "48-72) — the same definition for every year, regardless of which real "
            "weekday it fell on. \"Partial\" means the edition hasn't run that long "
            "(yet, or ever) — its last day's figures cover fewer than 24 real hours."
        ),
        "donations.no_day_evolution": "Not enough historical data to break down by day yet.",
        "donations.column.year": "Year",
        "donations.column.day": "Day",
        "donations.column.cumulative": "Total by day's end (€)",
        "donations.column.delta": "Raised that day (€)",
        "donations.column.avg_per_hour": "Avg. €/hour that day",
        "donations.column.status": "Status",
        "donations.day_complete": "Complete",
        "donations.day_partial": "Partial (in progress)",
        "donations.explain.day_evolution": (
            "\"Raised that day\" is the day's own delta, not a running total — day 2's "
            "figure is *only* what came in during hours 24-48, already excluding day "
            "1's total. Watch the average €/hour on a \"Partial\" day carefully: every "
            "edition's donations surge hardest in its final hours (confirmed across "
            "every year in this table), so a short partial window ending mid-surge can "
            "show a higher average rate than any complete day before it — a real "
            "number, not an error, but not a stable rate to extrapolate from either."
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
        "streamers.rank.efficiency": "€ per viewer",
        "streamers.top_n": "Show top N",
        "streamers.kpi.top": "Top by {metric}",
        "streamers.kpi.total_raised": "Total raised (shown)",
        "streamers.kpi.total_messages": "Total chat messages (shown)",
        "streamers.chart.ranked": "Streamers by {metric}",
        "streamers.correlation_heading": "Audience vs. engagement",
        "streamers.correlation_caption": (
            "Each point is a streamer — bubble size is donations raised, color is donation "
            "efficiency (€ per viewer). Useful for spotting high-viewer/low-chat (or the "
            "reverse) outliers, and streamers whose audience converts to donations "
            "unusually well or poorly for their size."
        ),
        "streamers.chart.correlation": "Avg. viewers vs. chat messages",
        "streamers.correlation_stat": (
            "Pearson r = {r} between avg. viewers and chat messages, across the streamers shown "
            "(1 = perfectly linear together, 0 = no linear relationship, negative = one rises as "
            "the other falls). This measures *linear* association only, and association isn't "
            "causation — a third factor (e.g. time slot) can drive both."
        ),
        "streamers.correlation_stat_na": (
            "Not enough streamers shown (or no variation in one axis) to compute a correlation."
        ),
        "streamers.efficiency_axis": "€ / viewer",
        "streamers.profile_heading": "Streamer profile",
        "streamers.pick_streamer": "Pick streamers to compare (up to 4)",
        "streamers.pick_at_least_one": "Pick at least one streamer above to see their profile.",
        "streamers.kpi.peak_viewers": "Peak viewers",
        "streamers.kpi.uptime": "Uptime",
        "streamers.kpi.top_category": "Top category",
        "streamers.kpi.unique_chatters": "Unique chatters",
        "streamers.uptime_quirk": "100%+ (data quirk)",
        "streamers.column.streamer": "Streamer",
        "streamers.radar_caption": (
            "This streamer's percentile rank against every streamer in the event, across "
            "five metrics at once — the dashed line marks the 50th percentile (the median "
            "streamer) as a baseline to compare the shape against."
        ),
        "streamers.chart.radar": "{streamer}'s profile vs. the field",
        "streamers.chart.radar_compare": "Selected streamers' profile vs. the field",
        "streamers.radar.donations": "Donations",
        "streamers.radar.audience": "Audience",
        "streamers.radar.engagement": "Engagement",
        "streamers.radar.efficiency": "€/viewer",
        "streamers.radar.uptime": "Uptime",
        "streamers.radar.median": "Median streamer",
        "streamers.explain.radar": (
            "Each axis is a percentile rank (0-100) against every streamer, not a raw "
            "value — donations and viewer counts aren't on the same scale, so raw numbers "
            "on one radar would be meaningless; percentile puts them on one comparable "
            "footing. A shape that bulges outward past the dashed median line is where "
            "this streamer leads the field; a dent inward is where they trail it."
        ),
        "streamers.chart.loyalty_mix": "{streamer}'s chatter loyalty mix",
        "streamers.chart.loyalty_mix_compare": "Chatter loyalty mix — selected streamers",
        "streamers.no_diurnal_data": "No hourly viewer pattern available yet for the selected streamer(s).",
        "streamers.chart.diurnal": "Hourly viewer pattern vs. event average",
        "streamers.hour_of_day": "hour of day (Europe/Paris)",
        "streamers.event_average": "Event average",
        "streamers.explain.ranked": (
            "The top N streamers ranked by whichever metric is selected above — donations, "
            "chat messages, or average viewers. One bar per streamer, longest first."
        ),
        "streamers.explain.correlation": (
            "Each point is a streamer: horizontal position is average viewers, vertical "
            "position is chat messages, bubble size is donations raised, and color is "
            "donations per viewer (gold = more efficient). A point far from the rest is "
            "worth a closer look — e.g. lots of viewers but a quiet chat, or a small bubble "
            "with a bright color (little raised overall, but efficient per viewer)."
        ),
        "streamers.explain.loyalty_mix": (
            "How many of this streamer's chatters only chat here (loyal) vs. also chat on "
            "other channels during the event (multi-streamer, semi-nomad, nomad)."
        ),
        "streamers.top_chatters_heading": "Top chatters",
        "streamers.top_chatters_caption_all": (
            "The most active chatters across all {n} streamers — event-wide, like the rest "
            "of this page, not affected by the sidebar date filter."
        ),
        "streamers.top_chatters_caption_filtered": (
            "The most active chatters across the {n} streamers matching the filters above — "
            "event-wide, like the rest of this page, not affected by the sidebar date filter."
        ),
        "streamers.chart.top_chatters": "Top {n} chatters",
        "streamers.explain.top_chatters": (
            "Each chatter's messages summed across only the streamers in scope above (not "
            "their whole-event total) — hover a bar to see how many of those streamers' "
            "channels they actually posted in, since a high total spread across several "
            "channels reads differently than the same total from one channel alone."
        ),
        "streamers.explain.diurnal": (
            "Average viewers by hour of day for each selected streamer (solid line) vs. the "
            "event-wide average (dotted) — shows whether their peak hours line up with, or "
            "differ from, everyone else's."
        ),
        "streamers.night_shift_caption": (
            "Donation euros raised per viewer, by hour of day — muted bars mark overnight hours."
        ),
        "streamers.night_shift_compare_note": (
            "Only shown for a single streamer — the overnight highlighting doesn't read "
            "cleanly once several streamers' bars are mixed together. Narrow your pick above "
            "to one streamer to see it."
        ),
        "streamers.chart.night_shift": "Donation efficiency by hour of day — {streamer}",
        "streamers.night_shift_axis": "€ per viewer",
        "streamers.explain.night_shift": (
            "Some streamers raise disproportionately more per viewer during overnight "
            "hours — a small, loyal audience giving generously — even though total "
            "viewership is lower then."
        ),
        # --- games ---
        "games.description": (
            "Twitch channel metadata: which categories were played and when, the hour-by-"
            "hour viewer leaderboard across channels, category switches' viewer impact, "
            "and recent stream sessions."
        ),
        "games.kpi.concurrent_now": "Concurrent viewers now",
        "games.kpi.channels_now": "Live channels now",
        "games.kpi.peak_concurrent": "Peak concurrent viewers",
        "games.chart.viewership": "Event-wide concurrent viewership",
        "games.chart.live_channels": "Live channels over time",
        "games.no_viewership": "No viewership data available yet.",
        "games.viewer_race_heading": "Viewer leaderboard, hour by hour",
        "games.no_viewer_race": "No per-channel viewership ranking available yet.",
        "games.viewer_race_top_n": "Show top N channels",
        "games.viewer_race_caption": (
            "The top channels overall by average viewers, hour by hour — each channel's "
            "full history in the window, not just the hours it led."
        ),
        "games.chart.viewer_race": "Top channels by viewers, over time",
        "games.explain.viewer_race": (
            "One line per channel among the top N overall by average viewers; hover a "
            "point for its exact rank that hour among every channel. Unlike the "
            "event-wide viewership total above, this shows which specific channels were "
            "leading, and how that changed."
        ),
        "games.categories_heading": "Categories",
        "games.category_filter": "Filter categories",
        "games.chart.by_category": "Channel-hours by category",
        "games.no_categories": "No category data available yet.",
        "games.category_trend_heading": "Category popularity over time",
        "games.no_category_trend": "No hour-by-hour category data available yet.",
        "games.category_trend_caption": (
            "How many channels were playing each category, hour by hour — the top 7 "
            "categories by total channel-hours, plus \"Other\" for the rest."
        ),
        "games.chart.category_trend": "Channels playing each category, over time",
        "games.explain.category_trend": (
            "A stacked area per category: height is how many channels were playing it "
            "that hour. Good for spotting a category trending at a specific moment (e.g. "
            "everyone switching to the same game for a challenge) that the totals bar "
            "above it can't show."
        ),
        "games.sessions_heading": "Recent stream sessions",
        "games.no_sessions": "No stream sessions recorded yet.",
        "games.sessions_caption": (
            "Peak viewers per session, colored by whether viewership grew (green) or fell "
            "(red) from the session's start — the full table is in the expander below."
        ),
        "games.chart.sessions": "Peak viewers by session",
        "games.explain.sessions": (
            "One bar per recent stream session — height is peak viewers reached during "
            "it, color is whether viewership was higher or lower than when the session "
            "started."
        ),
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
        "games.switches_heading": "Category switches",
        "games.no_switches": "No category switches in this range yet.",
        "games.switches_caption": "Switches ranked by how much the viewer count moved afterward.",
        "games.chart.switches": "Biggest viewer swings after a category switch",
        "games.switches_axis": "Viewer change (next hour)",
        "games.explain.switches": (
            "Green means viewers grew in the hour after switching category, red means "
            "they dropped — ranked by the size of the swing either way. This is what happened "
            "*after* the switch, not proof the switch *caused* it — a natural day/night dip, "
            "the streamer simply going live around then, or another channel's own swing can "
            "move the number just as easily."
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
        "goals.ambition_heading": "Ambition vs. reality",
        "goals.no_ambition": "No goal-coverage data available yet.",
        "goals.ambition_caption": (
            "The streamers whose donation goals were, so far, the most out of reach — "
            "fitting, given how exaggerated goal amounts often are."
        ),
        "goals.chart.ambition": "Least-covered donation goals",
        "goals.ambition_axis": "% of goal total raised",
        "goals.explain.ambition": (
            "Total raised as a percentage of the streamer's combined goal amounts — a "
            "low number here is as likely to mean 'joke goal' as 'ambitious goal'."
        ),
        # --- chat ---
        "chat.description": "Message volume over time, the busiest channels, and the most-used emotes.",
        "chat.no_data": "No chat data available yet.",
        "chat.kpi.messages_this_hour": "Messages this hour",
        "chat.kpi.chatters_this_hour": "Unique chatters this hour",
        "chat.kpi.total_messages": "Total messages (event)",
        "chat.chart.activity": "Chat messages per hour (all channels)",
        "chat.message_race_heading": "Message leaderboard, hour by hour",
        "chat.no_message_race": "No per-channel message ranking available yet.",
        "chat.message_race_top_n": "Show top N channels",
        "chat.message_race_caption": (
            "The top channels overall by chat messages, hour by hour — each channel's "
            "full history in the window, not just the hours it led."
        ),
        "chat.chart.message_race": "Top channels by messages, over time",
        "chat.explain.message_race": (
            "One line per channel among the top N overall by message count; hover a "
            "point for its exact rank that hour among every channel. Unlike the "
            "event-wide message volume above, this shows which specific channels were "
            "busiest, and how that changed."
        ),
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
        "chat.heatmap_caption": (
            "Brighter/more vivid green = more messages in that channel, that hour; a blank "
            "cell means the channel simply wasn't active that hour."
        ),
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
            "One cell per channel x hour; brighter means more messages, and an empty cell "
            "means that channel had no recorded activity that hour. Good for spotting "
            "which channels were active at which times, at a glance."
        ),
        "chat.spikes_heading": "Chat spikes",
        "chat.no_spikes": "No standout chat moments in this range yet.",
        "chat.spikes_caption": (
            "Hours where a channel's message volume deviated most from its own average."
        ),
        "chat.chart.spikes": "Biggest message-volume anomalies",
        "chat.spikes_axis": "Standard deviations from the channel's own average",
        "chat.explain.spikes": (
            "Each bar is one channel-hour, scored against that channel's own average and "
            "spread — so a normally-quiet channel's ordinary hour won't outrank a "
            "genuinely unusual moment for a busier one. Red/orange mark the most extreme."
        ),
        "chat.explain.composition": (
            "Each channel's messages split by who sent them (subscriber, VIP, moderator, "
            "plain viewer) — a high subscriber/moderator share suggests an established "
            "community, not just raw volume."
        ),
        "chat.verbosity_heading": "Message length by channel",
        "chat.verbosity_caption": (
            "How long a typical message is in each channel, in characters — a chat can be "
            "high-volume and still low-effort (short spam/emote-only messages), or lower-"
            "volume but more substantive."
        ),
        "chat.chart.verbosity": "Average message length by channel",
        "chat.verbosity_axis": "characters / message",
        "chat.explain.verbosity": (
            "Average character count per message in that channel, event-wide — a rough "
            "proxy for chat depth, not sentiment or quality."
        ),
        "chat.explain.emotes": (
            "The most-used emotes across the event, by usage count. Emotes not yet in the "
            "catalog are shown by a shortened id instead of their real code (see the note "
            "above the chart, if any are unnamed)."
        ),
        "chat.emote_search_heading": "Search by emote",
        "chat.emote_search_caption": "Find every chat message using a specific emote — who sent it, and where.",
        "chat.emote_search_label": 'Emote code (e.g. "Kappa", "LUL")',
        "chat.emote_search_no_matches": "No emotes match that search.",
        "chat.emote_search_pick": "Which one?",
        "chat.emote_search_no_usage": "That emote wasn't used in the selected date range.",
        "chat.emote_search_results_caption": "{count} messages, most recent first (capped at 200).",
        "chat.breakdown_heading": "Message breakdown",
        "chat.breakdown_caption": (
            "Slice the event's messages by channel, chatter, time of day, or emote."
        ),
        "chat.breakdown_dimension": "Break down by",
        "chat.breakdown.by_channel": "Channel",
        "chat.breakdown.by_chatter": "Chatter",
        "chat.breakdown.by_time": "Time of day",
        "chat.breakdown.by_emote": "Emote",
        "chat.chart.breakdown_channel": "Messages by channel",
        "chat.chart.breakdown_chatter": "Messages by chatter",
        "chat.chart.breakdown_time": "Messages by time of day",
        "chat.chart.breakdown_emote": "Messages by emote",
        "chat.explain.breakdown": (
            "The top 7 slices by message count, plus a single \"Other\" slice for the "
            "long tail — a pie with more categories than that stops being readable. "
            '"Time of day" buckets every message into a 6-hour window in Europe/Paris '
            "wall-clock time, regardless of which day of the event it fell on."
        ),
        "chat.daypart.morning": "Morning (6am-12pm)",
        "chat.daypart.afternoon": "Afternoon (12pm-6pm)",
        "chat.daypart.evening": "Evening (6pm-12am)",
        "chat.daypart.night": "Night (12am-6am)",
        "chat.drilldown_heading": "Chatter ↔ channel drill-down",
        "chat.drilldown_caption": (
            "Pick one chatter to see their messages split across channels, or pick one "
            "channel to see its messages split across chatters — the same relationship, "
            "read in each direction."
        ),
        "chat.drilldown_chatter_heading": "One chatter, by channel",
        "chat.drilldown_pick_chatter": "Pick a chatter",
        "chat.drilldown_channel_heading": "One channel, by chatter (inverse)",
        "chat.drilldown_pick_channel": "Pick a channel",
        "chat.chart.drilldown_chatter": "{chatter}'s messages by channel",
        "chat.chart.drilldown_channel": "{channel}'s messages by chatter",
        "chat.explain.drilldown": (
            "Left: one chatter's messages, split across every channel they chatted in. "
            "Right: the inverse — one channel's top chatters. The channel side is "
            "approximate: the chatter leaderboard tracks one (primary) channel per "
            "chatter, not their full per-channel activity, so a chatter who mostly "
            "chats elsewhere but occasionally drops into this channel may not appear. "
            "Only channels with at least one leaderboard chatter are offered, so the "
            "picker never lands on a guaranteed-empty choice."
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
            "more shared chatters, and node color is a detected community (channels whose "
            "audiences overlap most tend to cluster together, not an arbitrary per-channel "
            "color). Pick an hour to see how the community structure evolved; it opens on "
            "the latest hour with computed data, since the very newest hour of a live "
            "event can briefly lag behind."
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
            "edges mean more shared chatters, and node color is a detected community, "
            "same as the hour-by-hour graph above. Only the biggest hubs keep a permanent "
            "label; hover any node for its name."
        ),
        "community.chart.network": "Shared-audience network",
        "community.network_min_weight": "Minimum shared chatters to show a connection",
        "community.network_filtered_caption": (
            "Showing {edges} of {total_edges} connections ({nodes} of {total_nodes} channels) "
            "— raise the slider for a clearer picture, lower it to see more of the long tail."
        ),
        "community.weight_picker": "Weight connections by",
        "community.weight.shared_count": "Shared chatters (raw count)",
        "community.weight.jaccard": "Jaccard index (normalized overlap)",
        "community.weight.jaccard_caveat": (
            "Jaccard index = shared chatters ÷ chatters in *either* channel — two small "
            "channels that share most of their (small) audiences can outrank two huge "
            "channels with more shared chatters in absolute terms but a smaller overlap "
            "relative to their size. Raw count favors big channels; this favors tight-knit "
            "ones regardless of size."
        ),
        "community.weight.shared_count_hover_label": "shared chatters",
        "community.weight.jaccard_hover_label": "Jaccard overlap",
        "community.explain.growth": (
            "The cumulative count of distinct chatters seen so far, over time — always "
            "flat or rising."
        ),
        "community.retention_heading": "Chatter retention, day by day",
        "community.no_retention": "Not enough days of data yet to measure retention.",
        "community.retention_caption": (
            "Of the chatters active on the event's very first day, how many came back on "
            "each day after — event-wide, not affected by the sidebar date filter."
        ),
        "community.retention_day_label": "Day {day}",
        "community.chart.retention": "Day-0 chatters still active, by day",
        "community.retention_live_caveat": (
            "⚠️ If the event is still live, the most recent day shown is still in progress "
            "— its figure is a floor, not a final count."
        ),
        "community.explain.retention": (
            "\"Day\" is counted from the event's own start (its first message), not the "
            "calendar clock — day 0 is the first full 24 hours, day 1 the next, and so on. "
            "The percentage is the share of day-0 chatters still chatting that day; a "
            "chatter who left and came back later still counts."
        ),
        "community.new_by_channel_heading": "New chatters by channel",
        "community.no_new_by_channel": "No new-chatter data in this range yet.",
        "community.new_by_channel_caption": (
            "Top {shown} of {total} channels by first-time chatters brought in."
        ),
        "community.chart.new_by_channel": "New chatters per channel",
        "community.explain.new_by_channel": (
            'A chatter counts as "new to this channel" the first time they message '
            "there — even a loyal chatter elsewhere in the event counts as new here."
        ),
        "community.explain.hourly_network": (
            "One node per channel, one edge per pair of channels that shared chatters "
            "that hour — thicker/darker edges mean more shared chatters. Nodes are colored "
            "by detected community (modularity clustering: which channels' audiences "
            "overlap with each other more than with the rest) and positioned near their "
            "community's own cluster, so structure is visible at a glance instead of a "
            "random tangle. Node size tracks total shared audience (weighted degree); "
            "only the biggest hubs get a permanent label — hover any node for its name, "
            "or an edge for its exact shared-chatter count."
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
            "with, colored by detected community and positioned near its cluster; one edge "
            "per channel pair, thicker/darker for more shared chatters. Event-wide, unlike "
            "the hour-by-hour graph above it. Hover a node for its name and degree, or an "
            "edge for its exact shared-chatter count."
        ),
        "community.migrations_heading": "Channel hopping",
        "community.no_migrations": "No channel-hopping data available yet.",
        "community.migrations_caption": "How often chatters move directly from one channel to another.",
        "community.chart.migrations": "Chatter migrations between channels",
        "community.explain.migrations": (
            "A flow diagram, not a network graph: migrations are directed (and a channel "
            "pair often has hops in both directions), so each channel appears once on the "
            "left as an origin and once on the right as a destination. Band width scales "
            "with how many chatters made that specific hop — hover a band for the exact "
            "count. Event-wide, not affected by the sidebar date filter."
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
        "tracker.pick_streamer_single": (
            "Showing **{streamer}** — narrowed by the sidebar streamer filter."
        ),
        "tracker.category_filter": "Goal category",
        "tracker.category_filter_help": (
            "Each category is tracked as its own independent start/complete chain — mixing "
            "several on the timeline below can show unrelated goals' time spans crossing "
            "each other, so narrow to one to read it cleanly."
        ),
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
        "tracker.column.category": "Category",
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
        "chatters.correlation_stat": (
            "Pearson r = {r} between channel breadth and total messages, across the chatters "
            "shown (1 = perfectly linear together, 0 = no linear relationship). Linear "
            "association only — it doesn't imply one causes the other."
        ),
        "chatters.correlation_stat_na": (
            "Not enough chatters shown (or no variation in one axis) to compute a correlation."
        ),
        "chatters.lifespan_heading": "How long chatters stick around",
        "chatters.lifespan_caption": (
            "Time between a chatter's first and last message — a proxy for how engaged "
            "they were, not just how much they posted."
        ),
        "chatters.chart.lifespan": "Chatters by engagement lifespan",
        "chatters.lifespan.single_message": "Single message",
        "chatters.lifespan.under_1h": "< 1 hour",
        "chatters.lifespan.1_to_6h": "1 - 6 hours",
        "chatters.lifespan.6_to_24h": "6 - 24 hours",
        "chatters.lifespan.24h_plus": "24+ hours",
        "chatters.explain.lifespan": (
            "\"Single message\" means their first and last message are the same one — "
            "typically a drive-by chatter, not necessarily a bot (see the bot heuristic "
            "above for that). The right-hand bars are chatters who kept coming back over "
            "hours, sometimes the whole event."
        ),
        "chatters.profile_heading": "Chatter profile",
        "chatters.pick_chatter": "Pick a chatter for a detailed profile",
        "chatters.kpi.global_total": "Total messages (all channels)",
        "chatters.kpi.channels": "Channels chatted in",
        "chatters.kpi.top_channel_share": "Share of messages in top channel",
        "chatters.kpi.account_age": "Account age",
        "chatters.kpi.regularity": "Message-timing regularity",
        "chatters.regularity_help": (
            "Coefficient of variation of the time between this chatter's messages — a low "
            "value means very regular timing, one bot-likelihood signal among others."
        ),
        "chatters.no_channel_data": "No per-channel activity available yet for this chatter.",
        "chatters.chart.global_bar_label": "Global (all channels)",
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
        "chatters.by_channel_heading": "Chatters in one channel",
        "chatters.by_channel_caption": (
            "Pick a channel to see everyone who chatted there — badge type (subscriber/VIP/"
            "moderator/plain viewer), message count, first/last activity, and emote usage."
        ),
        "chatters.pick_channel": "Pick a channel",
        "chatters.badge_filter": "Filter by badge",
        "chatters.kpi.moderators": "Moderators",
        "chatters.kpi.subscribers": "Subscribers",
        "chatters.chart.badge_mix": "{channel}'s messages by chatter badge",
        "chatters.explain.badge_mix": (
            "Each chatter counts toward exactly one badge tier here (moderator/broadcaster > "
            "VIP > subscriber > plain viewer — Twitch's own display order), based on the "
            "badges attached to their messages in this channel, so the tiers never overlap."
        ),
        "chatters.rank.emotes": "Emote uses",
        "chatters.chart.channel_ranked": "{channel}'s chatters by {metric}",
        "chatters.explain.channel_ranked": (
            "The top N chatters in this channel, ranked by whichever metric is selected "
            "above — total messages, or total emote uses (summed from every emote in every "
            "one of their messages, not just distinct emotes)."
        ),
        "chatters.by_channel_table_caption": (
            "One row per chatter, with their badge-tier message counts, first/last message "
            "time, and total emote usage in this channel."
        ),
        # --- messages ---
        "messages.title": "Chat Messages",
        "messages.description": (
            "Search and browse individual chat messages by datetime, streamer, and chatter."
        ),
        "messages.no_data": "No chat data available yet.",
        "messages.filters": "Filters",
        "messages.channel_filter": "Streamer",
        "messages.all_channels": "All streamers",
        "messages.chatter_search": "Chatter contains",
        "messages.text_search": "Message contains",
        "messages.limit_label": "Max results",
        "messages.limit_caveat": (
            "Showing the {limit} most recent matching messages — narrow the filters to see "
            "further back."
        ),
        "messages.kpi.shown": "Messages shown",
        "messages.kpi.channels": "Streamers",
        "messages.kpi.chatters": "Chatters",
        "messages.time_heading": "When these messages happened",
        "messages.time_caption": (
            "Hourly count of the messages currently shown above (after filters and the "
            "result limit) — not the full event-wide activity chart on the Live Chat page."
        ),
        "messages.chart.time": "Messages shown, over time",
        "messages.explain.time": (
            "Bucketed by hour. If the result count hit the max-results limit, this only "
            "covers the most recent matching messages, not every match in the selected "
            "date range — narrow the filters to see further back."
        ),
        "messages.breakdown_heading": "Who and where",
        "messages.breakdown_caption": (
            "Top channels and chatters among the messages currently shown — same "
            "limit-truncation caveat as the chart above."
        ),
        "messages.chart.top_channels": "Top streamers, by messages shown",
        "messages.chart.top_chatters": "Top chatters, by messages shown",
        "messages.explain.breakdown": (
            "The busiest streamers and chatters within the current search results, not "
            "event-wide — e.g. searching a specific word shows who says it most, not who "
            "chats the most overall."
        ),
        "messages.table_heading": "Messages",
        "messages.table_caption": "Most recent matching messages first.",
        "messages.column.datetime": "Sent at",
        "messages.column.streamer": "Streamer",
        "messages.column.chatter": "Chatter",
        "messages.column.message": "Message",
        "messages.column.badge": "Badge",
        "messages.chart.badge_mix": "Messages shown, by chatter badge",
        "messages.explain.badge_mix": (
            "How the messages currently shown split across moderator, VIP, subscriber, "
            "and plain-viewer badges."
        ),
        # --- leaderboard ---
        "leaderboard.title": "Leaderboard",
        "leaderboard.description": (
            "Who's winning, all in one place — top streamers by donations and audience, top "
            "chatters, and each streamer's #1 fan. Event-wide standings, not a moving window."
        ),
        "leaderboard.no_data": "No streamer data available yet.",
        "leaderboard.top_n": "Show top N",
        "leaderboard.column.rank": "Rank",
        "leaderboard.column.streamer": "Streamer",
        "leaderboard.column.amount": "Amount",
        "leaderboard.column.chatter": "Chatter",
        "leaderboard.column.top_fan": "Top fan",
        "leaderboard.column.messages": "Messages",
        "leaderboard.donations_heading": "Top streamers by donations",
        "leaderboard.donations_caption": (
            "Event-wide totals — the same figures as the Donations page's own podium and the "
            "Streamers page's donation ranking, consolidated here."
        ),
        "leaderboard.chart.donations_podium": "Top 3 by donations raised",
        "leaderboard.explain.donations": (
            "Ranked by total donations raised, event-wide, regardless of the sidebar date filter."
        ),
        "leaderboard.chatters_heading": "Top chatters, event-wide",
        "leaderboard.chatters_caption": (
            "The most active chatters across the whole event — same figures as the Chatters "
            "page's own ranking, consolidated here."
        ),
        "leaderboard.chart.chatters_podium": "Top 3 by messages sent",
        "leaderboard.explain.chatters": (
            "Ranked by total messages sent, event-wide, across every channel a chatter posted in."
        ),
        "leaderboard.fans_heading": "Top fan, per streamer",
        "leaderboard.fans_caption": (
            "For every streamer, the single chatter who posted the most messages in their "
            "channel — not shown anywhere else in the app. Search by streamer name to jump "
            "to one."
        ),
        "leaderboard.fans_search": "Search by streamer name",
        "leaderboard.explain.fans": (
            "One row per streamer: their busiest individual chatter and how many messages "
            "that chatter sent there. A streamer's #1 fan doesn't need to be a globally "
            "top-ranked chatter — a small streamer's most active viewer can rank highly here "
            "while barely registering event-wide."
        ),
        "leaderboard.audience_heading": "Top streamers by audience & efficiency",
        "leaderboard.audience_caption": (
            "The first two metrics mirror the Streamers page's own ranking (minus "
            "donations, covered above); the three efficiency ones are new — different "
            "denominators (per viewer, per chatter, per hour) tell different stories about "
            "how well a streamer converts their stream into donations. Pick one to see who "
            "leads it."
        ),
        "leaderboard.metric_picker": "Rank by",
        "leaderboard.metric.viewers": "Audience (avg. viewers)",
        "leaderboard.metric.engagement": "Chat engagement (messages)",
        "leaderboard.metric.efficiency": "€ per viewer",
        "leaderboard.metric.efficiency_chatters": "€ per unique chatter",
        "leaderboard.metric.rate": "€ per hour streamed",
        "leaderboard.rate_caveat": (
            "⚠️ A streamer live only a few hours can post an extreme rate off a single big "
            "donation — this is a real ratio, not a bug, but treat a very short "
            "`hours_live` as a reason to look closer, not as proof of sustained pace."
        ),
        "leaderboard.chart.audience_podium": "Top 3 by {metric}",
        "leaderboard.explain.audience": (
            "Ranked by whichever metric is selected above — average viewers, chat messages, "
            "donations per viewer or per unique chatter (audience-efficiency, two "
            "different denominators — a chatter is a more engaged subset of viewers), or "
            "donations per hour actually streamed (time-efficiency, independent of "
            "audience size)."
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
        # --- about ---
        "about.title": "About",
        "about.description": "What this dashboard is, where its data comes from, and how it's built.",
        "about.what_heading": "What is ZEvent?",
        "about.what_body": (
            "[ZEvent](https://zevent.fr) is a French charity gaming marathon: dozens of "
            "Twitch streamers broadcast together for a fixed stretch (this run: "
            "**September 3-6, 2026**), and viewers donate live to a cause chosen ahead of "
            "the event. It's one of the largest charity streaming events in the "
            "French-speaking world."
        ),
        "about.dashboard_heading": "What this dashboard does",
        "about.dashboard_body": (
            "This app is a read-only window onto the event's data warehouse, updated as "
            "the event happens. It covers donations, streamer performance, games/categories, "
            "donation goals, live chat, the chatter community, and per-streamer activity — "
            "nine pages in total, linked from the home page."
        ),
        "about.pipeline_heading": "How the data flows",
        "about.pipeline_body": (
            "Two independent pipelines feed the warehouse: ZEvent's own donations/goals "
            "site, and Twitch's stream/chat metadata — the latter streamed in through "
            "[Apache NiFi](https://nifi.apache.org/). Both land in the same PostgreSQL "
            "warehouse, modeled with [dbt](https://www.getdbt.com/) across four schema "
            "layers, each building on the one before it:"
        ),
        "about.pipeline.raw": "Untouched, as-ingested data — the Twitch chat firehose and ZEvent donation-site snapshots, exactly as captured.",
        "about.pipeline.stg": "Bronze-layer staging — raw records normalized into a consistent shape (types, column names) without changing their meaning.",
        "about.pipeline.int": "Intermediate models — per-chatter, per-channel, per-hour aggregates built from staging (e.g. \"messages per channel per hour\").",
        "about.pipeline.marts": "Query-ready marts — the tables this dashboard actually reads from, one or more per page (e.g. the chatter leaderboard, the donation timeseries).",
        "about.pipeline.column_schema": "Schema",
        "about.pipeline.column_purpose": "Purpose",
        "about.technical_heading": "For data engineers, analysts, and ML engineers",
        "about.technical_intro": (
            "The rest of this page is for anyone who wants the actual "
            "engineering behind these charts, not just what they show. Every "
            "technique below was chosen and verified against real ZEvent "
            "data — where something didn't work, that's said plainly, not "
            "smoothed over."
        ),
        "about.technical_dataeng_heading": "Data engineering",
        "about.technical_dataeng_body": (
            "**Querying a 8M+-row, unindexed table safely.** "
            "`stg.stg_bronze__live_chat` (the raw chat firehose) has no index "
            "and grows continuously through the live event — any per-row "
            "text function (regex matching, string search) run over it "
            "directly risks the warehouse's 15-second statement timeout. "
            "Every query against it instead samples first "
            "(`WHERE random() < :sample_rate`), *then* runs the expensive "
            "per-row work only over the sample — cutting the row count "
            "before the costly part runs, not after.\n\n"
            "**Point-in-time reads under a live event.** Several charts "
            "(the donation-forecasting snapshot, leaderboard movers, "
            "channel timeseries leaderboards) need \"the most recent value "
            "as of some past moment,\" not just \"the current value\" — "
            "implemented as `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY "
            "ingested_at DESC)` filtered to `rn = 1`, scoped to rows at or "
            "before the cutoff.\n\n"
            "**Caching, tiered by how fast the data actually changes.** Live "
            "event queries cache for 60 seconds (`st.cache_data(ttl=60)`); "
            "database catalog stats (the section above) cache for 5 minutes "
            "— they change far more slowly than event figures, so a short "
            "TTL would just re-run the same catalog scan for the same "
            "answer; past-edition history (fetched externally, frozen "
            "forever) caches with no TTL at all. A pooled, bounded "
            "SQLAlchemy `Engine` (`st.cache_resource`) is shared across "
            "every concurrent session rather than one connection per "
            "visitor."
        ),
        "about.technical_stats_heading": "Statistical & heuristic analysis (Chat Intelligence)",
        "about.technical_stats_body": (
            "Chat Intelligence is deliberately dependency-light: word-list "
            "matching and counting, no trained model. Every word list was "
            "tested against real chat before being kept — several intuitive "
            "first guesses for a hostility list (\"con\", \"stupide\", "
            "\"pourri\") were tried and rejected because real data showed "
            "them mostly hitting something else entirely (a game title, a "
            "Twitch emote code, harmless slang). Matching uses a "
            "*leading*-only word boundary (Postgres' `\\y` anchor on one "
            "side only), not a plain substring and not a boundary on both "
            "sides — verified to be the one setting that avoids emote-code "
            "false positives (`\"melokaIdiot\"`) without also dropping real "
            "plurals and emphasis-lengthened forms (`\"connards\"`, "
            "`\"CONNASSEEEE\"`) as false negatives."
        ),
        "about.technical_ml_heading": "Real machine learning (Chat ML Lab)",
        "about.technical_ml_body": (
            "**Clustering** (`sklearn.cluster.KMeans`) segments both message "
            "topics (channel-hour-pooled chat, TF-IDF over lemmatized "
            "unigrams+bigrams) and streamer/chatter behavior (performance and "
            "activity-shape features, log1p-transformed and standardized "
            "first — real donation/activity figures are heavily right-skewed, "
            "confirmed against real data). A 2D PCA projection of the same "
            "feature space the clustering fit on lets those segments "
            "actually be *seen*, not just tabulated.\n\n"
            "**Outlier detection** (`sklearn.ensemble.IsolationForest`) flags "
            "streamers, chatters, and chat-mood hours whose shape is "
            "statistically unusual — confirmed to surface both extremes at "
            "once (the event's biggest fundraisers *and* near-inactive "
            "placeholder entries), with the expected-outlier-fraction "
            "exposed as a tunable slider.\n\n"
            "**Donation forecasting** (`sklearn.ensemble.RandomForestRegressor`) "
            "predicts a streamer's *eventual final* donation total from a "
            "snapshot of their own donations/viewers/messages at an earlier, "
            "real point in time — deliberately not from their own final "
            "stats, which would be near-tautological. Evaluated honestly on "
            "a held-out 25% test split, not on the training data.\n\n"
            "**Pretrained transformer classification** (`transformers`) "
            "compares real sentiment/toxicity models against the lexicon "
            "heuristic above. Model choice was verified, not assumed: a "
            "smaller multilingual toxicity model confidently mislabeled a "
            "wholesome message as 99% toxic and missed a genuine insult "
            "entirely, before being swapped for one that got every real test "
            "message right.\n\n"
            "**Linguistic analysis** (spaCy's French pipeline) adds "
            "lemmatization, part-of-speech tagging, dependency parsing, "
            "named-entity recognition, and both static (word2vec/GloVe-style) "
            "and contextual (transformer-derived) word/message embeddings. "
            "NER is the one technique here with an honestly weak spot on this "
            "text: a generic French model, trained on formal writing, still "
            "misreads some Twitch emote codes and chat slang as real "
            "entities even after filtering — stated in the page itself, not "
            "hidden."
        ),
        "about.technical_principles_heading": "Working principles",
        "about.technical_principles_body": (
            "1. **Verify against real data before shipping, not just "
            "documentation.** Several techniques above were tried, found "
            "wanting on real ZEvent chat, and replaced or filtered — that's "
            "the normal path, not an exception.\n"
            "2. **State a model's real limitations in the UI itself.** A "
            "toxicity flag, an NER hit, or a forecast is a lead to look at "
            "in context, never presented as a certified verdict.\n"
            "3. **Design out circularity.** A forecast predicts a genuinely "
            "*future* value from a genuinely *past* snapshot — never a "
            "number from a restatement of itself.\n"
            "4. **Respect the database's real constraints.** Sample before "
            "the expensive per-row work, not after; a 15-second statement "
            "timeout is a hard budget, not a suggestion."
        ),
        "about.infra_heading": "Infrastructure & monitoring",
        "about.infra_body": (
            "The pipeline and its hosting are provisioned as code (infrastructure as "
            "code), not set up by hand. [Prometheus](https://prometheus.io/) and "
            "[Grafana](https://grafana.com/) monitor the pipeline and warehouse "
            "(ingestion lag, job failures, table freshness), and "
            "[ntfy](https://ntfy.sh/) pushes alerts when something needs attention — "
            "this dashboard is a read-only consumer of the warehouse those alerts "
            "protect, not part of the alerting path itself."
        ),
        "about.freshness_heading": "Data freshness",
        "about.freshness_body": (
            "Every page query is cached for 60 seconds, so the numbers you see can lag the "
            "live event by up to a minute. Because this is a *live* event, a few marts need "
            "an hour to fully close before they're computed for it — most visibly, the "
            "chatter-community network's most recent hour can briefly show no data until "
            "that hour's pipeline run catches up. This dashboard picks the latest hour that "
            "already has data by default, so you shouldn't normally see it — but it's why "
            "the hour picker can still land on an empty one if you scrub to the very edge."
        ),
        "about.privacy_heading": "Privacy",
        "about.privacy_body": (
            "Twitch usernames are real and shown on-screen, same as they'd appear in the "
            "channel itself. Any CSV export that includes a chatter identifier replaces it "
            "with a one-way pseudonym first (see the Chatters page), so a downloaded file "
            "can never be traced back to a real person."
        ),
        "about.stack_heading": "Built with",
        "about.stack_body": (
            "[Streamlit](https://streamlit.io) for the app itself, "
            "[Polars](https://pola.rs) for every in-app transform, "
            "[Plotly](https://plotly.com/python/) for the charts, "
            "[dbt](https://www.getdbt.com/) + PostgreSQL for the warehouse, all in Python."
        ),
        "about.related_heading": "Related projects",
        "about.related_body": (
            "This app is part of a small ecosystem: `zevent-analysis` (deeper offline "
            "analysis), `zevent-db` (the warehouse this app reads from), and "
            "`zevent-infra-monitoring` (pipeline/infra monitoring). This dashboard is "
            "currently the only one of the four with a working deliverable."
        ),
        # --- chat intelligence ---
        "chatintel.title": "Chat Intelligence",
        "chatintel.description": (
            "Lightweight, no-training-data analysis of live chat text: which channels' "
            "chat is most excitable, positive, or hostile; which messages are being "
            "copy-pasted; and which words are trending in one channel's chat over time. "
            "See \"How these measures are computed\" below for the exact methodology."
        ),
        "chatintel.methodology_heading": "How these measures are computed",
        "chatintel.methodology_intro": (
            "Every measure below is a lexicon/heuristic — counting words and patterns "
            "— not a trained machine-learning model. That's deliberate, not a "
            "shortcut: real ZEvent chat is short, French, emote-heavy, and unlabeled, "
            "and a plain regex over the underlying ~7.7 million message table "
            "reliably times out at full scale (see \"Sampling\" near the bottom). In "
            "every formula, $p_x$ means \"the fraction of sampled messages matching "
            "condition $x$.\""
        ),
        "chatintel.methodology_hype_intro": (
            "Hype score (0-100) — a blend of heavy punctuation, ALL-CAPS shouting, "
            "and hype-emote mentions, weighted 40/30/30:"
        ),
        "chatintel.methodology_hype_terms": (
            "p_punct = messages containing \"!!\" or more · p_caps = whole-message "
            "ALL-CAPS with at least 4 letters · p_emote = messages mentioning a known "
            "hype emote."
        ),
        "chatintel.methodology_hype_tunable": (
            "The weights (w) default to 0.4/0.3/0.3 but are yours to tune — see the "
            "sliders in the Chat hype meter section below."
        ),
        "chatintel.methodology_sentiment_intro": (
            "Sentiment score (-100 to +100) — positive-word rate minus hostile-word "
            "rate:"
        ),
        "chatintel.methodology_toxicity_intro": (
            "Toxicity score (0-100) — that same hostile-word rate alone:"
        ),
        "chatintel.methodology_words_intro": (
            "The exact word lists currently in use — every word here was tested "
            "individually against real chat before being kept; several intuitive "
            "first guesses (\"con\", \"cretin\", \"stupide\", \"pourri\") failed and were "
            "dropped, see below. Matching also requires a word boundary right "
            "before the word (not a bare substring): a real-data audit found "
            "\"idiot\" as a plain substring also matched Twitch emote codes "
            "(\"melokaIdiot\") and someone's actual username being mentioned "
            "(\"@je_un_idiot\") — a word boundary rules both out, while still "
            "catching plurals and emphasis-lengthened forms (\"connards\", "
            "\"CONNASSEEEE\") a *stricter* boundary on both sides would have missed."
        ),
        "chatintel.methodology_positive_words_label": "Positive words:",
        "chatintel.methodology_hype_emote_words_label": "Hype-emote words:",
        "chatintel.methodology_hostile_words_label": "Hostile words:",
        "chatintel.methodology_examples_pointer": (
            "Curious what actually counts as \"hostile\"? Open \"See example flagged "
            "messages\" under Chat toxicity below to check real matches yourself."
        ),
        "chatintel.methodology_keywords_intro": (
            "Trending keywords — TF-IDF over one channel's messages, pooling all of "
            "an hour's text into one \"document\":"
        ),
        "chatintel.methodology_keywords_terms": (
            "N_hours = total hours in the channel's history · df(w) = number of "
            "hours word w appears in at least once."
        ),
        "chatintel.methodology_phrases_intro": (
            "Trending phrases — no formula needed: the same message (lowercased, "
            "whitespace-trimmed) sent at least 5 times within one channel's one "
            "hour, counted directly."
        ),
        "chatintel.methodology_correlation_intro": (
            "Chat mood vs. donation pace — the standard Pearson correlation "
            "coefficient between the event-wide hourly mood score and that hour's "
            "donation pace:"
        ),
        "chatintel.methodology_sampling_intro": (
            "Sampling — every channel-wide measure above (hype, sentiment, "
            "toxicity, trending phrases) runs on a random sample sized to stay "
            "fast, not every message:"
        ),
        "chatintel.methodology_sampling_terms": (
            "N_target = 250,000 messages (300,000 for trending phrases) · N_total "
            "= messages in the selected window. A window already smaller than the "
            "target uses every message (sample_rate = 1)."
        ),
        "chatintel.methodology_toxicity_privacy": (
            "The toxicity *score* above is a channel-level trend by design — it's "
            "about which channels' chat is running hot, not about singling out a "
            "chatter. The example messages below it, and the ML Lab's own toxicity "
            "tools, do show the real chatter who sent a flagged message (same as "
            "every other chatter-listing page in this app) — but the heuristic still "
            "gets things wrong (see the word list above and its known false "
            "positives), so treat a flag as something to check in context, not a "
            "verdict on the person."
        ),
        "chatintel.no_streamers": "No streamer data available yet.",
        "chatintel.hype_heading": "Chat hype meter",
        "chatintel.hype_weight_punct": "Punctuation weight",
        "chatintel.hype_weight_caps": "ALL-CAPS weight",
        "chatintel.hype_weight_emote": "Hype-emote weight",
        "chatintel.hype_top_n": "Show top N channels",
        "chatintel.hype_caption": (
            "The top channels overall by chat \"hype\" — a heuristic blend of "
            "exclamation-heavy messages, ALL-CAPS shouting, and hype-emote mentions, "
            "not raw message volume. A smaller, more excitable community can out-hype a "
            "much bigger, calmer one. Drag the three weights below to change how much "
            "each signal counts — the chart recomputes instantly, no reload needed."
        ),
        "chatintel.chart.hype": "Chat hype score, over time",
        "chatintel.unit.hype_score": "hype score",
        "chatintel.no_hype": "No hype data available yet.",
        "chatintel.explain.hype": (
            "Hype score (0-100) blends three signals per message, averaged per hour: "
            "\"!!\"-or-more punctuation, whole-message ALL-CAPS shouting, and mentions of "
            "well-known hype emotes (LUL, KEKW, PogChamp, ...) — weighted by the three "
            "sliders above (0.4/0.3/0.3 by default). The three raw rates are fetched "
            "once per date range and the weighting is recomputed in the browser, so "
            "moving a slider never re-queries the database. Computed from a random "
            "sample of that hour's messages (hours with too few sampled messages are "
            "dropped) rather than a full scan, since a live per-message analysis over "
            "the whole event is too slow to run on demand. Hover a point for its exact "
            "rank that hour among every channel."
        ),
        "chatintel.sentiment_heading": "Chat sentiment",
        "chatintel.sentiment_top_n": "Show top N channels",
        "chatintel.sentiment_caption": (
            "The most positive channels overall, hour by hour — positive-word rate minus "
            "hostile-word rate. Not the same as hype above: a channel can be highly "
            "positive without being loud, or loud without being especially positive."
        ),
        "chatintel.chart.sentiment": "Chat sentiment score, over time",
        "chatintel.unit.sentiment_score": "sentiment score",
        "chatintel.no_sentiment": "No sentiment data available yet.",
        "chatintel.explain.sentiment": (
            "Sentiment score (-100 to +100) is a curated positive-word rate (\"merci\", "
            "\"super\", \"bravo\", \"excellent\", ...) minus the same hostile-word rate "
            "toxicity (below) uses, averaged per hour, computed the same sampled way as "
            "hype (see \"How these measures are computed\" above). Hover a point for its "
            "exact rank that hour among every channel."
        ),
        "chatintel.toxicity_heading": "Chat toxicity",
        "chatintel.toxicity_top_n": "Show top N channels",
        "chatintel.toxicity_caption": (
            "The most hostile channels overall, hour by hour — how the chat's most "
            "negative language shifts between channels over the event. This tracks "
            "*channels*, not chatters: no chatter is ever named or flagged as \"toxic\" "
            "here, on purpose (see \"How these measures are computed\" above)."
        ),
        "chatintel.chart.toxicity": "Chat toxicity score, over time",
        "chatintel.unit.toxicity_score": "toxicity score",
        "chatintel.no_toxicity": "No toxicity data available yet.",
        "chatintel.explain.toxicity": (
            "Toxicity score (0-100) is a curated hostile-word rate (\"connard\", "
            "\"idiot\", \"dégage\", \"ta gueule\", ...), averaged per hour, computed the "
            "same sampled way as hype (see \"How these measures are computed\" above). "
            "It measures hostile-language density, not a certified harassment/hate-speech "
            "classifier — it will miss slurs and hostility that avoid these exact words, "
            "and can't tell a targeted insult from banter between friends. Hover a point "
            "for its exact rank that hour among every channel."
        ),
        "chatintel.toxicity_examples_heading": "See example flagged messages",
        "chatintel.toxicity_examples_caption": (
            "A random sample of messages the hostile-word list above matched in the "
            "selected window — check the heuristic's work yourself. Shows the real "
            "channel and chatter, same as the Chatters/Streamers/Community pages — "
            "but the word list still makes mistakes (see the false-positive caveat "
            "above), so treat a match here as a lead to look at, not a verdict."
        ),
        "chatintel.no_toxicity_examples": "No flagged messages in the selected range yet.",
        "chatintel.column.chatter": "Chatter",
        "chatintel.column.message": "Message",
        "chatintel.correlation_heading": "Chat mood vs. donation pace",
        "chatintel.correlation_caption": (
            "Does chat excitement or positivity actually track how much is being "
            "donated? Hype and sentiment here are averaged across every channel each "
            "hour, not just the top N — a single, event-wide mood per hour, matched "
            "against that same hour's donation pace."
        ),
        "chatintel.no_correlation": "Not enough overlapping hours to compute a correlation yet.",
        "chatintel.correlation_summary": (
            "Over {n} hours: hype correlates at r = {hype_corr} with donation pace; "
            "sentiment correlates at r = {sentiment_corr}. A coefficient near 0 means no "
            "relationship, near +1/-1 a strong one — with only a few dozen hours, treat "
            "these as a rough signal, not a precise measurement, and remember "
            "correlation isn't causation."
        ),
        "chatintel.chart.correlation": "Chat hype vs. donation pace, one point per hour",
        "chatintel.explain.correlation": (
            "Each point is one hour: its event-wide average hype score (x-axis) against "
            "how much was donated that hour (y-axis). A point cloud that trends upward "
            "left-to-right suggests hype and giving move together that hour; a flat or "
            "scattered cloud suggests they don't. Computed from "
            "`chat_mood_timeseries` (same sampling as hype/sentiment above) joined to "
            "the donations page's own hourly pace."
        ),
        "chatintel.phrases_heading": "Trending phrases & copypasta",
        "chatintel.phrases_top_n": "Show top N phrases",
        "chatintel.phrases_caption": (
            "The most-repeated exact messages (case/whitespace normalized) sent within "
            "one channel's one hour, event-wide — Twitch chat's classic \"copypasta\" "
            "pattern: the same line spammed by many chatters in a burst."
        ),
        "chatintel.no_phrases": "No repeated phrases found yet.",
        "chatintel.column.hour": "Hour",
        "chatintel.column.channel": "Channel",
        "chatintel.column.phrase": "Phrase",
        "chatintel.column.repeat_count": "Repeat count",
        "chatintel.explain.phrases": (
            "Counted from a random sample of each hour's messages, not a full scan (same "
            "reason as the hype meter above) — real repeat counts are higher than shown. "
            "Only phrases repeated at least 5 times within the sampled hour are kept, to "
            "filter out coincidental short messages a couple of chatters happened to both "
            "send once."
        ),
        "chatintel.keywords_heading": "Trending keywords per channel",
        "chatintel.pick_channel": "Pick a channel",
        "chatintel.keywords_caption": (
            "One channel's most distinctive chat words, hour by hour — a word that "
            "suddenly spikes in one hour (a shoutout, a running joke, a donation-goal "
            "reveal) ranks above words used at a similar low rate all the time."
        ),
        "chatintel.no_keywords": "No chat data available for this channel yet.",
        "chatintel.column.keywords": "Top keywords",
        "chatintel.explain.keywords": (
            "Uses every message from the selected channel (no sampling needed — a single "
            "channel's messages are cheap to fetch in full). Each hour's words are scored "
            "by TF-IDF: how often a word appears that hour, weighted up the rarer it is "
            "across the channel's other hours — the same statistic search engines use to "
            "tell a distinctive word from a common one. No sentiment or topic model is "
            "involved."
        ),
        # --- chat ml lab ---
        "chatml.title": "Chat ML Lab",
        "chatml.description": (
            "Real, trained machine-learning models over live chat — heavier and slower "
            "than Chat Intelligence's word-list heuristics, for questions those can't "
            "answer: what topics does chat actually discover, what behavioral chatter "
            "segments exist, and does a real model even agree with the lexicon?"
        ),
        "chatml.topics_heading": "Message topic clusters",
        "chatml.topics_caption": (
            "Real unsupervised clustering (K-Means over TF-IDF), not keyword ranking — "
            "each channel's hour of chat is pooled into one \"document\" and grouped "
            "with similar hours across the whole event, discovering actual topics (a "
            "Twitch-plays-style voting moment, a channel's own emote-heavy banter, "
            "donation-goal talk, ...) rather than just counting words."
        ),
        "chatml.topics_n_clusters": "Number of topic clusters",
        "chatml.no_topics": "Not enough messages in the selected range to form topic clusters yet.",
        "chatml.chart.topics": "Topic cluster sizes (channel-hours)",
        "chatml.column.cluster": "Cluster",
        "chatml.column.channel_hours": "Channel-hours",
        "chatml.column.top_terms": "Top terms",
        "chatml.explain.topics": (
            "Each channel-hour with enough sampled messages becomes one TF-IDF "
            "\"document\"; K-Means groups similar documents together. A cluster's "
            "\"top terms\" are the words that most define its centroid — not "
            "necessarily its single most common word, but the words that most "
            "distinguish it from every other cluster. Clustering raw individual "
            "messages was tried first and rejected: real chat messages are so short "
            "that almost all of them ended up in one meaningless catch-all cluster; "
            "pooling by channel-hour first fixes that.\n\n"
            "Words are lemmatized before counting (spaCy's French pipeline) — "
            "\"joue\"/\"jouait\"/\"jouer\" collapse into one shared term instead of "
            "splitting a topic's signal across inflected forms — and a `word word` "
            "term (space-joined here, underscore-joined internally) is a bigram: two "
            "words scored as one phrase, not two separate hits. Twitch emote codes "
            "and copy-paste spam are filtered out before scoring (see the "
            "Linguistic analysis section below for exactly how, and where that "
            "filtering still lets noise through)."
        ),
        "chatml.linguistics_heading": "Linguistic analysis (NLP)",
        "chatml.linguistics_caption": (
            "Real linguistic structure over a sample of chat text, via spaCy's "
            "French pipeline (`fr_core_news_md`) and the toxicity model's own "
            "encoder — part-of-speech tagging, dependency parsing, named-entity "
            "recognition, static word embeddings, and contextual message "
            "embeddings. Every technique here was run against real ZEvent chat "
            "before being kept — see each subsection's \"How to read this chart\" "
            "for what worked and, honestly, what didn't."
        ),
        "chatml.no_linguistics": "Not enough messages in the selected range to run linguistic analysis.",
        "chatml.pos_heading": "Part-of-speech distribution",
        "chatml.column.pos": "POS tag",
        "chatml.column.count": "Count",
        "chatml.chart.pos_distribution": "How often each grammatical role appears in chat",
        "chatml.explain.pos": (
            "Universal POS tags (spaCy's tagset): `NOUN`/`PROPN` (common/proper "
            "nouns), `VERB`, `ADJ`, `ADV`, `PRON` (pronouns), `DET` (determiners — "
            "\"le\"/\"la\"/\"un\"), `ADP` (prepositions — \"de\"/\"pour\"), `INTJ` "
            "(interjections), `PUNCT`. A chat dominated by short reactions and "
            "interjections over full sentences shows up here as a real, "
            "measurable skew toward `INTJ`/`PUNCT`/`PRON` relative to formal "
            "written French — not just an impression from reading a few messages."
        ),
        "chatml.ner_heading": "Named entities mentioned",
        "chatml.column.entity": "Entity",
        "chatml.column.label": "Type",
        "chatml.chart.entities": "Most frequently mentioned named entities",
        "chatml.explain.ner": (
            "**Honest limitation, not a hidden one.** This is a general-purpose "
            "French NER model — trained on formal written text, not Twitch chat — "
            "and it will still misread some emote codes and chat slang as real "
            "entities even after filtering (verified against real ZEvent chat: "
            "\"MegaphoneZ\", a hype-train emote, was read as a person 200+ times "
            "before an emote-code filter was added; some noise, like all-caps "
            "shouting or emote codes with no interior capital, still gets through). "
            "The filter removes text with a mid-word capital "
            "(`\"MegaphoneZ\"`, `\"adfaceBZZZ\"` — real proper nouns only ever "
            "capitalize their first letter), repeated-letter spam (`\"MDRRR\"`), "
            "and a short list of common chat interjections. What survives — "
            "`PER` (person), `LOC` (place), `ORG` (organization), `MISC` — trends "
            "toward real signal (streamer names, game titles) the more a mention "
            "recurs, since one-off misclassifications rarely repeat as often as a "
            "genuine, frequently-discussed entity."
        ),
        "chatml.parse_heading": "Dependency parse",
        "chatml.parse_input_label": "Message to parse",
        "chatml.parse_caption": (
            "Every word's grammatical role and what it depends on — the structure "
            "a reader uses to parse a sentence without thinking about it, made "
            "explicit. Try pasting a real chat message, in French or English."
        ),
        "chatml.column.token": "Token",
        "chatml.column.lemma": "Lemma",
        "chatml.column.dependency": "Dependency",
        "chatml.column.head": "Depends on",
        "chatml.explain.parse": (
            "`dependency` is the token's grammatical relation to its `head` — "
            "e.g. `nsubj` (nominal subject), `amod` (adjectival modifier), `det` "
            "(determiner), `ROOT` (the sentence's main verb/predicate, which "
            "depends on nothing — its own `head` is itself). Reading `head` for "
            "every row reconstructs the sentence's whole dependency tree without "
            "needing a diagram: follow each word up to what it modifies, up to "
            "the `ROOT`."
        ),
        "chatml.word_embeddings_heading": "Word embeddings: a semantic map of chat vocabulary",
        "chatml.chart.word_embeddings": "Frequent content words, projected by meaning (PCA of word vectors)",
        "chatml.explain.word_embeddings": (
            "Each word gets one fixed 300-dimension vector from spaCy's static "
            "word-embedding table (trained on general French text, not this "
            "chat), projected here to 2D — words the model considers similar in "
            "meaning or usage land near each other, regardless of anything "
            "specific to ZEvent. \"Static\" is the key word: unlike the "
            "contextual embeddings below, a word has exactly one vector no "
            "matter which message it appears in — this is the classic sense of "
            "\"word embeddings\" (word2vec/GloVe-style), one fixed table, not a "
            "trained-per-context representation."
        ),
        "chatml.contextual_embeddings_heading": "Contextual embeddings: the same word, different meanings",
        "chatml.contextual_embeddings_caption": (
            "Unlike the static word vectors above, a contextual embedding "
            "depends on the *sentence* a word sits in, not just the word itself "
            "— the same word can land in a different place depending on what "
            "surrounds it. Reuses the toxicity classifier's own encoder purely "
            "as a general-purpose multilingual text encoder (its classification "
            "head isn't used here) — one 768-dimension vector per message, "
            "mean-pooled from real (non-padding) token positions, then projected "
            "to 2D. Gated behind a button, same reason as the ML classification "
            "section: this loads a large transformer model, not run "
            "automatically."
        ),
        "chatml.contextual_embeddings_button": "Compute contextual embeddings",
        "chatml.contextual_embeddings_hint": (
            "Click \"Compute contextual embeddings\" above to load the model and "
            "see a 2D map of real messages — not run automatically, since it can "
            "download ~2GB the first time."
        ),
        "chatml.contextual_embeddings_spinner": "Computing contextual embeddings...",
        "chatml.chart.contextual_embeddings": "A sample of real messages, projected by contextual meaning",
        "chatml.no_word_embeddings": "Not enough distinct content words in the sample to map.",
        "chatml.streamers_heading": "Streamer behavioral segments",
        "chatml.streamers_caption": (
            "Real unsupervised clustering (K-Means) over each streamer's performance "
            "shape — donations raised, audience size, hours live, uptime — grouping "
            "streamers by how their event went, not by category or team (there is no "
            "team dimension in this data)."
        ),
        "chatml.streamers_n_clusters": "Number of behavioral segments",
        "chatml.no_streamers_ml": (
            "Not enough streamers in the selected range to form behavioral segments yet."
        ),
        "chatml.column.streamers": "Streamers",
        "chatml.column.avg_amount": "Avg. donations (€)",
        "chatml.column.avg_avg_viewers": "Avg. viewers",
        "chatml.column.avg_hours_live": "Avg. hours live",
        "chatml.column.avg_uptime_pct": "Avg. uptime %",
        "chatml.column.streamer": "Streamer",
        "chatml.column.amount": "Donations (€)",
        "chatml.column.avg_viewers_short": "Avg. viewers",
        "chatml.streamers_examples_heading": "See example streamers per cluster",
        "chatml.explain.streamers": (
            "Every feature is log-transformed before clustering, same reasoning as "
            "chatter segments below — real donation/audience figures are heavily "
            "skewed (confirmed against real data: total donations range from €0 to "
            "over €2M against a €3.3k median), and without that transform a handful "
            "of mega-fundraisers would dominate cluster formation instead of the "
            "shape of the bulk of the field."
        ),
        "chatml.chatters_heading": "Chatter behavioral segments",
        "chatml.chatters_caption": (
            "Real unsupervised clustering (K-Means) over each chatter's activity "
            "shape — how many channels they visit, how much they post, how long they "
            "stick around — richer than a fixed \"sedentary / nomadic\" label since "
            "the segments are discovered from the data itself, not defined ahead of "
            "time. Likely-bot accounts are excluded first."
        ),
        "chatml.chatters_n_clusters": "Number of behavioral segments",
        "chatml.no_chatters": (
            "Not enough chatters in the selected range to form behavioral segments yet."
        ),
        "chatml.column.chatters": "Chatters",
        "chatml.column.chatter": "Chatter",
        "chatml.column.avg_channels": "Avg. channels",
        "chatml.column.avg_messages": "Avg. messages",
        "chatml.column.avg_lifespan_hours": "Avg. lifespan (h)",
        "chatml.column.avg_messages_per_channel": "Avg. messages / channel",
        "chatml.chatters_examples_heading": "See example chatters per cluster",
        "chatml.explain.chatters": (
            "Every feature is log-transformed before clustering — real chatter "
            "activity is heavily skewed (a handful of accounts post thousands of "
            "times more than the median), and without that transform a few extreme "
            "accounts would dominate cluster formation instead of the shape of the "
            "bulk of the population. Compare a cluster's own averages against the "
            "others' to see what defines it — a high avg. messages/channel with few "
            "channels visited reads as \"loyal superfan\"; many channels with few "
            "total messages reads as \"channel-hopping lurker\"."
        ),
        "chatml.outliers_heading": "Outlier detection",
        "chatml.outliers_caption": (
            "Real unsupervised anomaly detection (Isolation Forest) — flags "
            "streamers, chatters, or chat-mood hours whose numbers look nothing like "
            "the typical case, in *either* direction. Confirmed against real data: "
            "this surfaces both the event's biggest fundraisers and its "
            "near-inactive placeholder entries as \"statistically unusual\" at once — "
            "an outlier isn't automatically a problem, just unusual."
        ),
        "chatml.outliers_target_label": "Look for outliers among",
        "chatml.outliers_target_streamers": "Streamers",
        "chatml.outliers_target_chatters": "Chatters",
        "chatml.outliers_target_hours": "Chat-mood hours",
        "chatml.outliers_contamination": "Expected outlier fraction",
        "chatml.no_outliers": "Not enough rows in the selected range to detect outliers yet.",
        "chatml.column.uptime_pct": "Uptime %",
        "chatml.column.anomaly_score": "Anomaly score",
        "chatml.column.hour": "Hour",
        "chatml.column.avg_hype": "Avg. hype score",
        "chatml.column.avg_sentiment": "Avg. sentiment score",
        "chatml.explain.outliers": (
            "\"Expected outlier fraction\" is Isolation Forest's one tuning knob — "
            "raise it to see more (and less extreme) rows flagged, lower it to see "
            "only the most extreme few. \"Anomaly score\" is the model's own "
            "decision function: more negative means more anomalous, so the most "
            "unusual rows sort first. Streamer/chatter features are log-transformed "
            "first for the same skew reasons as their clustering sections above; "
            "chat-mood hours are not, since sentiment can be negative."
        ),
        "chatml.classify_heading": "Real model vs. lexicon: sentiment & toxicity",
        "chatml.classify_caption": (
            "Runs actual pretrained transformer models (not word lists) over a small "
            "sample of messages — some already flagged as hostile by Chat "
            "Intelligence's lexicon, some random — and compares their verdict to the "
            "lexicon's. Loads ~1-2GB of model weights the first time (cached after "
            "that); click to run. Shows the real channel and chatter — but neither "
            "the model nor the lexicon is a certified classifier, so read a "
            "\"toxic\"/\"hostile\" flag as a lead to check in context, not a verdict."
        ),
        "chatml.classify_button": "Run ML classification",
        "chatml.classify_spinner": (
            "Running sentiment and toxicity models (may download ~1-2GB the first "
            "time)..."
        ),
        "chatml.no_classify": "No messages available to classify in the selected range.",
        "chatml.classify_agreement": (
            "The ML toxicity model and the lexicon heuristic agree on {pct}% of this "
            "sample. Where they disagree is usually where context matters — see the "
            "table below."
        ),
        "chatml.column.channel_short": "Channel",
        "chatml.column.message": "Message",
        "chatml.column.lexicon_verdict": "Lexicon says hostile",
        "chatml.column.ml_sentiment": "ML sentiment",
        "chatml.column.ml_toxicity": "ML toxicity",
        "chatml.explain.classify": (
            "Sentiment model: cardiffnlp/twitter-xlm-roberta-base-sentiment "
            "(multilingual, trained on social-media text). Toxicity model: "
            "textdetox/xlmr-large-toxicity-classifier — chosen after testing against "
            "real chat: a smaller alternative confidently mislabeled \"gg les gars, "
            "quel beau run\" (a friendly message) as 99% toxic and missed a real "
            "insult entirely. A model can read context the lexicon can't — e.g. "
            "recognizing \"ta gueule\" between friends as mostly playful rather than "
            "hostile — which is exactly why comparing the two is worth doing rather "
            "than trusting either alone."
        ),
        "chatml.classify_hint": (
            "Click \"Run ML classification\" above to load the models and see a "
            "comparison — not run automatically, since it can download ~1-2GB the "
            "first time."
        ),
        "chatml.column.pca1": "Principal component 1",
        "chatml.column.pca2": "Principal component 2",
        "chatml.chart.streamers_pca": "Streamer segments, projected to 2D (PCA)",
        "chatml.streamers_pca_caption": (
            "Each dot is one streamer, colored by its behavioral cluster above — "
            "the same 7-feature space the clustering was fit on, projected down to "
            "the 2 directions of greatest variation so the segments can actually be "
            "seen, not just tabulated. Distance on this plot roughly tracks how "
            "similar two streamers' performance shape is, not their raw earnings. "
            "Hover any point for that streamer's name and Twitch channel."
        ),
        "chatml.explain.streamers_pca": (
            "Three steps turn the 7 raw features "
            "(`amount_eur`, `hours_live`, `avg_viewers`, `peak_viewers`, "
            "`unique_chatters`, `total_messages`, `uptime_pct`) into the 2 axes "
            "plotted above — the same steps `cluster_streamers` itself fits on, "
            "so this view matches the clusters exactly rather than being a "
            "separately-chosen projection:\n\n"
            "1. **Log-transform** each feature to tame its right skew "
            "(`amount_eur` alone ranges from near-zero to over €2M): "
            "$x' = \\log(1+x)$.\n"
            "2. **Standardize** so no single feature's raw scale dominates: "
            "$z = \\dfrac{x' - \\mu}{\\sigma}$, with mean $\\mu$ and standard "
            "deviation $\\sigma$ computed per feature across all streamers.\n"
            "3. **Project** each streamer's standardized 7-dimensional vector "
            "$z$ onto the top 2 principal components $w_1, w_2$ — the 2 "
            "directions of the 7-dimensional space (found via eigendecomposition "
            "of $z$'s covariance matrix) that capture the most variance: "
            "$\\mathrm{PC}_i = z \\cdot w_i$.\n\n"
            "The two axes don't correspond to any single original feature — each "
            "is a weighted mix of all seven — so read this plot for *relative* "
            "position and clustering, not as literal donation or viewer values."
        ),
        "chatml.chart.chatters_pca": "Chatter segments, projected to 2D (PCA)",
        "chatml.chatters_pca_caption": (
            "Same idea as the streamer PCA plot above, over the chatter behavioral "
            "feature space — each dot is one chatter, colored by cluster. Hover "
            "any point for that chatter's name."
        ),
        "chatml.explain.chatters_pca": (
            "Same log-transform → standardize → project pipeline as the streamer "
            "PCA plot above (see its \"How to read this chart\" for the formulas), "
            "run instead over the 6 chatter behavioral features "
            "(`distinct_channel_count`, `total_message_count`, `lifespan_hours`, "
            "`gap_coefficient_of_variation`, `avg_messages_per_channel`, "
            "`top_channel_share`) that `cluster_chatters` itself fits on."
        ),
        "chatml.forecast_heading": "Donation forecasting from a mid-event snapshot",
        "chatml.forecast_caption": (
            "A Random Forest regressor trained to predict each streamer's "
            "*eventual final* donation total from a snapshot of their own "
            "cumulative donations, viewers and chat activity at an earlier "
            "cutoff — genuinely forecasting an unknown future from a known past, "
            "not predicting a number from itself. Move the slider to see how "
            "forecast accuracy changes the earlier the snapshot is taken."
        ),
        "chatml.no_forecast": (
            "Not enough streamers in the selected range/filter to fit and evaluate "
            "a forecasting model yet."
        ),
        "chatml.forecast_cutoff": "Snapshot cutoff (fraction of the selected date range)",
        "chatml.forecast_cutoff_caption": "Snapshot taken as of: {cutoff}",
        "chatml.forecast_r2": "R² (test set)",
        "chatml.forecast_mae": "MAE (test set)",
        "chatml.forecast_n_test": "Streamers held out for testing",
        "chatml.forecast_perfect_line": "Perfect prediction",
        "chatml.forecast_scatter_name": "Streamer",
        "chatml.chart.forecast_scatter": "Predicted vs. actual final donations (test set)",
        "chatml.forecast_axis_actual": "Actual final donations (€)",
        "chatml.forecast_axis_predicted": "Predicted final donations (€)",
        "chatml.chart.forecast_importance": "What the model relies on most",
        "chatml.forecast_feature_amount": "Donations so far",
        "chatml.forecast_feature_avg_viewers": "Avg. viewers so far",
        "chatml.forecast_feature_peak_viewers": "Peak viewers so far",
        "chatml.forecast_feature_messages": "Chat messages so far",
        "chatml.explain.forecast": (
            "**Why this isn't circular.** Predicting a streamer's final total "
            "from their *own final* stats (e.g. final viewers) would be "
            "near-tautological — of course a number correlates with itself. "
            "This instead snapshots every feature strictly *before* the cutoff "
            "and only ever predicts what happens *after* it, the same "
            "past-only-predicts-future constraint any real forecasting problem "
            "needs.\n\n"
            "**Why log-transformed.** Donations, viewers and message counts are "
            "all heavily right-skewed (a few mega-fundraisers, a long tail of "
            "small ones) — fitting on $x' = \\log(1+x)$ keeps the model from "
            "being dominated by the biggest streamer alone, then predictions "
            "are converted back to euros ($x = e^{x'} - 1$) before scoring, so "
            "R²/MAE above are in the same units the chart shows.\n\n"
            "**Reading the metrics**, for $n$ test streamers with actual final "
            "totals $y_i$ and predicted totals $\\hat y_i$ (mean actual "
            "$\\bar y$):\n"
            "- $R^2 = 1 - \\dfrac{\\sum_i (y_i - \\hat y_i)^2}"
            "{\\sum_i (y_i - \\bar y)^2}$ — close to 1.0 means the snapshot "
            "explains almost all of the variation in final totals; 0 means it "
            "explains no more than always guessing the average.\n"
            "- $\\mathrm{MAE} = \\dfrac{1}{n}\\sum_i |y_i - \\hat y_i|$ — the "
            "average prediction error, in euros.\n\n"
            "Both are computed only on the held-out 25% test split — streamers "
            "the model never saw while fitting — an honest estimate of forecast "
            "error, not one inflated by testing on the training data itself."
        ),
    },
    "fr": {
        # --- common ---
        "common.mock_data_banner": (
            "Affichage de **données d'exemple** — connectez une base de données "
            "(`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) pour voir les vrais chiffres."
        ),
        "common.footer": (
            "ZEvent Dataviz v{version} — un tableau de bord non officiel pour le marathon "
            "caritatif [ZEvent](https://zevent.fr), non affilié à l'événement ni à ses "
            "organisateurs."
        ),
        "common.no_data_in_range": "Aucune donnée dans la plage sélectionnée.",
        "common.view_data": "Voir les données sous-jacentes",
        "common.download_csv": "⬇️ Télécharger le CSV",
        "common.prev_page": "⬅️ Précédent",
        "common.next_page": "Suivant ➡️",
        "common.page_of": "Page {page} sur {pages}",
        "common.pie_other": "Autres",
        "common.how_to_read": "💡 Comment lire ce graphique",
        "common.date_filter_caveat": (
            "Cette section reflète l'événement entier, pas le filtre de dates de la barre "
            "latérale — ces données sont pré-agrégées, sans horodatage par ligne."
        ),
        "common.entity_filter_caveat": (
            "Cette section n'est pas non plus filtrée par les streamers/chatteurs sélectionnés "
            "— ces données sont pré-agrégées, sans ventilation par chaîne/chatteur."
        ),
        "filter.date_range_label": "📅 Plage de dates",
        "filter.streamer_label": "🎙️ Streamers",
        "filter.chatter_label": "🗣️ Chatteurs",
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
        # --- nav ---
        "nav.info_section": "Infos",
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
            "vidéo français où des streamers collectent des dons pour une cause. Elle est "
            "en lecture seule, mise à jour directement depuis l'entrepôt au fil de "
            "l'événement."
        ),
        "home.about_link": "Comment fonctionne ce tableau de bord, et d'où viennent ses données",
        "home.kpi_heading": "Aperçu de l'événement",
        "home.kpi.total_raised": "Total collecté",
        "home.kpi.duration": "Durée de suivi des dons",
        "home.kpi.duration_value": "{hours} h",
        "home.kpi.streamers": "Streamers",
        "home.kpi.chatters": "Chatteurs",
        "home.kpi.messages": "Messages de chat",
        "home.kpi.peak_viewers": "Pic de viewers simultanés",
        "home.tech_expander_label": "🔧 Détails de la base de données (pour data engineers)",
        "home.tech_caption": (
            "L'entrepôt de données derrière chaque page de ce site : combien de "
            "tables existent dans chaque couche dbt, combien de lignes et "
            "d'espace disque elles occupent, et comment les données circulent de "
            "l'ingestion brute jusqu'aux marts que chaque page lit. Replié par "
            "défaut — ce sont des détails de data engineering, pas quelque chose "
            "dont chaque visiteur a besoin."
        ),
        "home.tech_no_data": (
            "Cette section reflète les métadonnées du catalogue de la vraie base "
            "de données et n'est pas disponible avec des données factices/de "
            "démonstration."
        ),
        "home.tech_kpi.tables": "Tables & vues",
        "home.tech_kpi.rows": "Lignes totales (estimation)",
        "home.tech_kpi.size": "Taille totale sur disque",
        "home.tech_chart.lineage": "Lignage des données : couches dbt, par nombre de tables",
        "home.tech_stage.raw": "raw",
        "home.tech_stage.stg": "stg (staging)",
        "home.tech_stage.int": "int (intermédiaire)",
        "home.tech_stage.marts": "marts",
        "home.tech_stage.pages": "les 14 pages de l'application",
        "home.explain.tech_lineage": (
            "La structure en couches de dbt elle-même, pas un graphe de "
            "dépendances table par table — Postgres ne conserve pas le SQL qui a "
            "construit une table matérialisée une fois qu'elle est construite, "
            "donc une flèche de lignage au niveau *table* (« ce mart lit "
            "exactement ces 3 modèles int ») n'est pas quelque chose que cette "
            "page peut honnêtement déduire de la seule base de données ; ce "
            "niveau de détail vit dans le `manifest.json` propre au projet dbt, "
            "pas dans la connexion en lecture seule de cette application à "
            "l'entrepôt qu'il a construit. Ce qui *est* réel : `raw` contient "
            "les données ingérées brutes et non modifiées ; `stg` les "
            "normalise en une forme cohérente sans changer leur sens ; `int` "
            "construit des agrégats par chatteur/par chaîne/par heure à "
            "partir du staging ; `marts` sont les tables prêtes à interroger "
            "que chaque page lit effectivement (voir "
            "`app/data/repository.py::PostgresDataSource` pour savoir "
            "exactement quel mart alimente quel graphique). La largeur des "
            "flux est le vrai nombre de tables de chaque couche, issu de la "
            "requête ci-dessous. Pour le vrai graphe de lignage par modèle, "
            "voir la documentation générée par dbt ci-dessous, si elle est "
            "hébergée."
        ),
        "home.tech_dbt_docs_button": "📖 Ouvrir les docs dbt (vrai lignage par modèle)",
        "home.tech_dbt_docs_hint": (
            "Aucune documentation dbt n'est encore reliée. Lancez `dbt docs "
            "generate` dans le projet d'entrepôt, hébergez le résultat (même "
            "un simple serveur de fichiers statiques suffit), et définissez "
            "`DBT_DOCS_URL` dans le `.env` de cette application pour afficher "
            "un lien ici."
        ),
        "home.tech_table.column.schema": "Schéma",
        "home.tech_table.column.table": "Table",
        "home.tech_table.column.kind": "Type",
        "home.tech_table.column.rows": "Lignes (est.)",
        "home.tech_table.column.size": "Taille",
        "home.tech_table.kind.table": "table",
        "home.tech_table.kind.view": "vue",
        "home.daily_heading": "Tendance quotidienne",
        "home.daily_caption": "Totaux de l'événement, regroupés par jour.",
        "home.chart.daily": "Dons par jour",
        "home.explain.daily": (
            "Une barre par jour calendaire de l'événement — une vue plus large que les "
            "graphiques horaires des autres pages, utile pour repérer le jour le plus généreux."
        ),
        "home.pages_heading": "Pages",
        # --- donations ---
        "donations.description": (
            "Dons cumulés sur la durée de l'événement, évolution du rythme heure par "
            "heure, et mouvements du classement."
        ),
        "donations.no_data": "Aucune donnée de dons disponible pour le moment.",
        "donations.kpi.total_raised": "Total collecté",
        "donations.kpi.active_streamers": "Streamers actifs (dernière heure)",
        "donations.kpi.best_hour": "Meilleure heure",
        "donations.podium_heading": "Meilleurs collecteurs",
        "donations.podium_caption": "Les 3 streamers ayant collecté le plus jusqu'à présent.",
        "donations.chart.podium": "Top 3 des dons collectés",
        "donations.explain.podium": (
            "Total des dons collectés par streamer, à l'échelle de l'événement (non "
            "affecté par le filtre de dates de la barre latérale) — la hauteur des barres "
            "est le montant réel, classé 1er/2e/3e."
        ),
        "donations.chart.cumulative": "Dons cumulés",
        "donations.chart.pace": "Rythme des dons (par heure)",
        "donations.donation_race_heading": "Classement des dons, heure par heure",
        "donations.no_donation_race": "Aucun classement de dons par chaîne disponible pour le moment.",
        "donations.donation_race_top_n": "Afficher le top N streamers",
        "donations.donation_race_caption": (
            "Les meilleurs streamers au global par dons cumulés, heure par heure — "
            "l'historique complet de chaque streamer sur la période, pas seulement les "
            "heures où il était en tête."
        ),
        "donations.chart.donation_race": "Meilleurs streamers par dons, dans le temps",
        "donations.explain.donation_race": (
            "Une ligne par streamer parmi le top N au global par dons cumulés ; survolez "
            "un point pour son classement exact cette heure-là parmi tous les streamers. "
            "Contrairement au total cumulé de l'événement ci-dessus, ceci "
            "montre quels streamers précisément étaient en tête, et comment cela a évolué."
        ),
        "donations.spikes_heading": "Pics remarquables",
        "donations.no_spikes": "Aucun don remarquable dans cette plage pour le moment.",
        "donations.spikes_caption": (
            "Les plus gros dons, avec ce qui était diffusé à l'écran à ce moment-là."
        ),
        "donations.explain.spikes": (
            "Chaque ligne est un don anormalement élevé — son titre/catégorie et l'activité "
            "du chat cette heure-là, pour comprendre ce qui a pu le déclencher."
        ),
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
        "donations.editions_heading": "Cette édition vs. les précédentes",
        "donations.editions_caption": (
            "Dons cumulés alignés sur le nombre d'heures depuis le début de chaque édition, "
            "pas sur la date calendaire, pour comparer les courbes directement. La courbe de "
            "cet événement vient des données de cette appli ; les courbes des éditions "
            "précédentes viennent de [EvenMoreStats](https://zevent.gdoc.fr) "
            "(evenmorestats.fr), un tracker ZEvent tiers non officiel — pas de l'entrepôt de "
            "données de cette appli."
        ),
        "donations.editions_unavailable": (
            "La comparaison avec les éditions précédentes est temporairement indisponible — "
            "impossible de joindre la source de données externe (EvenMoreStats)."
        ),
        "donations.chart.editions": "Dons cumulés par heures depuis le début",
        "donations.hours_since_start": "heures depuis le début de l'événement",
        "donations.editions_y_axis": "€ (échelle log)",
        "donations.explain.editions": (
            "Chaque année a sa propre couleur ; la ligne de cette année est tracée plus "
            "épaisse, mais chaque édition — y compris celle-ci — démarre son propre "
            "chronomètre à l'heure 0, donc une montée plus rapide en début d'événement ou "
            "un dépassement de seuil plus précoce se voit directement quand une courbe en "
            "dépasse une autre. L'axe des ordonnées est logarithmique (chaque graduation "
            "correspond à x10) pour qu'une édition au total final bien plus élevé n'aplatisse "
            "pas les autres courbes — y compris celle de cette année — en bas du graphique."
        ),
        "donations.day_evolution_heading": "Évolution jour par jour, à travers les éditions",
        "donations.day_evolution_caption": (
            "Chaque « jour » est une fenêtre fixe de 24 heures depuis le démarrage "
            "(heure 0-24, 24-48, 48-72) — la même définition pour chaque année, peu "
            "importe le jour de semaine réel où elle est tombée. « Partiel » signifie "
            "que l'édition n'a pas encore duré aussi longtemps (ou jamais) — les "
            "chiffres de son dernier jour couvrent moins de 24 heures réelles."
        ),
        "donations.no_day_evolution": (
            "Pas encore assez de données historiques pour une répartition par jour."
        ),
        "donations.column.year": "Année",
        "donations.column.day": "Jour",
        "donations.column.cumulative": "Total en fin de jour (€)",
        "donations.column.delta": "Récolté ce jour (€)",
        "donations.column.avg_per_hour": "€/heure moy. ce jour",
        "donations.column.status": "Statut",
        "donations.day_complete": "Complet",
        "donations.day_partial": "Partiel (en cours)",
        "donations.explain.day_evolution": (
            "« Récolté ce jour » est le delta propre au jour, pas un total cumulé — le "
            "chiffre du jour 2 est *uniquement* ce qui est arrivé pendant les heures "
            "24-48, excluant déjà le total du jour 1. Regardez attentivement la "
            "moyenne €/heure d'un jour « Partiel » : les dons de chaque édition "
            "explosent le plus dans ses dernières heures (confirmé pour chaque année "
            "de ce tableau), donc une courte fenêtre partielle se terminant en plein "
            "pic peut afficher un taux moyen plus élevé que n'importe quel jour "
            "complet précédent — un chiffre réel, pas une erreur, mais pas non plus "
            "un taux stable à extrapoler."
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
        "streamers.rank.efficiency": "€ par viewer",
        "streamers.top_n": "Afficher le top N",
        "streamers.kpi.top": "Premier par {metric}",
        "streamers.kpi.total_raised": "Total collecté (affiché)",
        "streamers.kpi.total_messages": "Total messages chat (affiché)",
        "streamers.chart.ranked": "Streamers par {metric}",
        "streamers.correlation_heading": "Audience vs. engagement",
        "streamers.correlation_caption": (
            "Chaque point est un streamer — la taille de la bulle représente les dons "
            "collectés, la couleur l'efficacité des dons (€ par viewer). Utile pour repérer "
            "les cas atypiques (forte audience / peu de chat, ou l'inverse), et les "
            "streamers dont l'audience convertit anormalement bien ou mal en dons pour "
            "leur taille."
        ),
        "streamers.chart.correlation": "Viewers moyens vs. messages du chat",
        "streamers.correlation_stat": (
            "r de Pearson = {r} entre viewers moyens et messages du chat, sur les streamers "
            "affichés (1 = relation linéaire parfaite, 0 = aucune relation linéaire, négatif = "
            "l'un monte quand l'autre baisse). Ceci ne mesure qu'une association *linéaire*, et "
            "association n'est pas causalité — un troisième facteur (ex. le créneau horaire) "
            "peut influencer les deux."
        ),
        "streamers.correlation_stat_na": (
            "Pas assez de streamers affichés (ou aucune variation sur un axe) pour calculer "
            "une corrélation."
        ),
        "streamers.efficiency_axis": "€ / viewer",
        "streamers.profile_heading": "Profil du streamer",
        "streamers.pick_streamer": "Choisir des streamers à comparer (4 max)",
        "streamers.pick_at_least_one": "Choisissez au moins un streamer ci-dessus pour voir son profil.",
        "streamers.kpi.peak_viewers": "Pic de viewers",
        "streamers.kpi.uptime": "Temps de live",
        "streamers.kpi.top_category": "Catégorie principale",
        "streamers.kpi.unique_chatters": "Chatteurs uniques",
        "streamers.uptime_quirk": "100%+ (anomalie de données)",
        "streamers.column.streamer": "Streamer",
        "streamers.radar_caption": (
            "Le rang percentile de ce streamer par rapport à tous les streamers de "
            "l'événement, sur cinq métriques à la fois — la ligne pointillée marque le "
            "50e percentile (le streamer médian) comme référence pour comparer la forme."
        ),
        "streamers.chart.radar": "Profil de {streamer} face au reste du champ",
        "streamers.chart.radar_compare": "Profil des streamers sélectionnés face au reste du champ",
        "streamers.radar.donations": "Dons",
        "streamers.radar.audience": "Audience",
        "streamers.radar.engagement": "Engagement",
        "streamers.radar.efficiency": "€/viewer",
        "streamers.radar.uptime": "Uptime",
        "streamers.radar.median": "Streamer médian",
        "streamers.explain.radar": (
            "Chaque axe est un rang percentile (0-100) par rapport à tous les streamers, "
            "pas une valeur brute — dons et nombres de viewers ne sont pas sur la même "
            "échelle, donc des valeurs brutes sur un même radar n'auraient aucun sens ; "
            "le percentile les met sur un pied d'égalité comparable. Une forme qui dépasse "
            "la ligne médiane pointillée est un point fort de ce streamer ; un creux vers "
            "l'intérieur est un point faible."
        ),
        "streamers.chart.loyalty_mix": "Mix de fidélité des chatteurs de {streamer}",
        "streamers.chart.loyalty_mix_compare": "Mix de fidélité des chatteurs — streamers sélectionnés",
        "streamers.no_diurnal_data": (
            "Aucun profil horaire de viewers disponible pour le(s) streamer(s) sélectionné(s)."
        ),
        "streamers.chart.diurnal": "Profil horaire de viewers vs. moyenne de l'événement",
        "streamers.hour_of_day": "heure de la journée (Europe/Paris)",
        "streamers.event_average": "Moyenne de l'événement",
        "streamers.explain.ranked": (
            "Le top N des streamers classés selon la métrique choisie ci-dessus — dons, "
            "messages du chat, ou viewers moyens. Une barre par streamer, la plus longue en premier."
        ),
        "streamers.explain.correlation": (
            "Chaque point est un streamer : la position horizontale est les viewers "
            "moyens, la verticale les messages du chat, la taille de la bulle les dons "
            "collectés, et la couleur les dons par viewer (doré = plus efficace). Un point "
            "isolé des autres mérite un coup d'œil — par exemple beaucoup de viewers mais "
            "un chat silencieux, ou une petite bulle à la couleur vive (peu collecté au "
            "total, mais efficace par viewer)."
        ),
        "streamers.explain.loyalty_mix": (
            "Combien des chatteurs de ce streamer ne discutent que chez lui (fidèles) "
            "contre ceux qui discutent aussi sur d'autres chaînes pendant l'événement "
            "(multi-streamer, semi-nomade, nomade)."
        ),
        "streamers.top_chatters_heading": "Meilleurs chatteurs",
        "streamers.top_chatters_caption_all": (
            "Les chatteurs les plus actifs sur les {n} streamers, à l'échelle de "
            "l'événement comme le reste de cette page, non affecté par le filtre de dates "
            "de la barre latérale."
        ),
        "streamers.top_chatters_caption_filtered": (
            "Les chatteurs les plus actifs sur les {n} streamers correspondant aux filtres "
            "ci-dessus — à l'échelle de l'événement comme le reste de cette page, non "
            "affecté par le filtre de dates de la barre latérale."
        ),
        "streamers.chart.top_chatters": "Top {n} chatteurs",
        "streamers.explain.top_chatters": (
            "Les messages de chaque chatteur cumulés uniquement sur les streamers "
            "concernés ci-dessus (pas leur total sur tout l'événement) — survolez une "
            "barre pour voir sur combien de ces chaînes ce chatteur a vraiment posté, car "
            "un total élevé réparti sur plusieurs chaînes ne se lit pas comme le même "
            "total venant d'une seule chaîne."
        ),
        "streamers.explain.diurnal": (
            "Viewers moyens par heure de la journée pour chaque streamer sélectionné (ligne "
            "pleine) vs. la moyenne de l'événement (pointillés) — montre si leurs heures de "
            "pointe correspondent à celles des autres, ou en diffèrent."
        ),
        "streamers.night_shift_caption": (
            "Euros de dons récoltés par viewer, par heure de la journée — les barres "
            "atténuées marquent les heures de nuit."
        ),
        "streamers.night_shift_compare_note": (
            "Affiché uniquement pour un seul streamer — la mise en avant des heures de nuit "
            "ne se lit pas clairement une fois les barres de plusieurs streamers mélangées. "
            "Réduisez votre sélection ci-dessus à un seul streamer pour le voir."
        ),
        "streamers.chart.night_shift": "Efficacité des dons par heure de la journée — {streamer}",
        "streamers.night_shift_axis": "€ par viewer",
        "streamers.explain.night_shift": (
            "Certains streamers récoltent proportionnellement plus par viewer pendant la "
            "nuit — une audience réduite mais fidèle et généreuse — même si l'audience "
            "totale est plus faible à ce moment-là."
        ),
        # --- games ---
        "games.description": (
            "Métadonnées des chaînes Twitch : quelles catégories étaient jouées et quand, "
            "le classement horaire des viewers entre chaînes, l'impact des changements de "
            "catégorie sur les viewers, et les sessions de stream récentes."
        ),
        "games.kpi.concurrent_now": "Viewers simultanés actuels",
        "games.kpi.channels_now": "Chaînes en direct actuellement",
        "games.kpi.peak_concurrent": "Pic de viewers simultanés",
        "games.chart.viewership": "Audience simultanée de l'événement",
        "games.chart.live_channels": "Chaînes en direct dans le temps",
        "games.no_viewership": "Aucune donnée d'audience disponible pour le moment.",
        "games.viewer_race_heading": "Classement des viewers, heure par heure",
        "games.no_viewer_race": "Aucun classement de viewers par chaîne disponible pour le moment.",
        "games.viewer_race_top_n": "Afficher le top N chaînes",
        "games.viewer_race_caption": (
            "Les meilleures chaînes au global par viewers moyens, heure par heure — "
            "l'historique complet de chaque chaîne sur la période, pas seulement les "
            "heures où elle était en tête."
        ),
        "games.chart.viewer_race": "Meilleures chaînes par viewers, dans le temps",
        "games.explain.viewer_race": (
            "Une ligne par chaîne parmi le top N au global par viewers moyens ; survolez "
            "un point pour son classement exact cette heure-là parmi toutes les chaînes. "
            "Contrairement au total d'audience de l'événement ci-dessus, ceci "
            "montre quelles chaînes précises étaient en tête, et comment ça a évolué."
        ),
        "games.categories_heading": "Catégories",
        "games.category_filter": "Filtrer les catégories",
        "games.chart.by_category": "Heures-chaîne par catégorie",
        "games.no_categories": "Aucune donnée de catégorie disponible pour le moment.",
        "games.category_trend_heading": "Popularité des catégories dans le temps",
        "games.no_category_trend": "Aucune donnée de catégorie heure par heure disponible pour le moment.",
        "games.category_trend_caption": (
            "Combien de chaînes jouaient à chaque catégorie, heure par heure — les 7 "
            "catégories les plus jouées en heures-chaîne, plus « Autres » pour le reste."
        ),
        "games.chart.category_trend": "Chaînes jouant à chaque catégorie, dans le temps",
        "games.explain.category_trend": (
            "Une aire empilée par catégorie : la hauteur indique combien de chaînes y "
            "jouaient cette heure-là. Utile pour repérer une catégorie qui décolle à un "
            "moment précis (ex. tout le monde bascule sur le même jeu pour un défi), ce "
            "que la barre des totaux ci-dessus ne peut pas montrer."
        ),
        "games.sessions_heading": "Sessions de stream récentes",
        "games.no_sessions": "Aucune session de stream enregistrée pour le moment.",
        "games.sessions_caption": (
            "Pic de viewers par session, coloré selon que l'audience a augmenté (vert) ou "
            "diminué (rouge) depuis le début de la session — le tableau complet est dans "
            "le menu déroulant ci-dessous."
        ),
        "games.chart.sessions": "Pic de viewers par session",
        "games.explain.sessions": (
            "Une barre par session de stream récente — la hauteur est le pic de viewers "
            "atteint pendant celle-ci, la couleur indique si l'audience était plus haute "
            "ou plus basse qu'au début de la session."
        ),
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
        "games.switches_heading": "Changements de catégorie",
        "games.no_switches": "Aucun changement de catégorie dans cette plage pour le moment.",
        "games.switches_caption": (
            "Changements classés par l'ampleur du mouvement de viewers qui a suivi."
        ),
        "games.chart.switches": "Plus gros mouvements de viewers après un changement de catégorie",
        "games.switches_axis": "Variation de viewers (heure suivante)",
        "games.explain.switches": (
            "Vert signifie que les viewers ont augmenté dans l'heure suivant le changement "
            "de catégorie, rouge qu'ils ont chuté — classé par l'ampleur du mouvement. Ceci "
            "montre ce qui s'est passé *après* le changement, pas la preuve que le changement "
            "en est la *cause* — un creux naturel jour/nuit, le streamer qui vient de se "
            "connecter, ou la propre variation d'une autre chaîne peuvent tout autant "
            "expliquer le chiffre."
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
        "goals.ambition_heading": "Ambition vs. réalité",
        "goals.no_ambition": "Aucune donnée de couverture d'objectifs disponible pour le moment.",
        "goals.ambition_caption": (
            "Les streamers dont les objectifs de dons sont, pour l'instant, les plus hors "
            "de portée — logique, vu à quel point les montants d'objectifs sont souvent exagérés."
        ),
        "goals.chart.ambition": "Objectifs de dons les moins couverts",
        "goals.ambition_axis": "% du total de l'objectif collecté",
        "goals.explain.ambition": (
            "Le total collecté en pourcentage de la somme des objectifs du streamer — un "
            "chiffre bas ici signifie autant « objectif blague » qu'« objectif ambitieux »."
        ),
        # --- chat ---
        "chat.description": (
            "Volume de messages dans le temps, les chaînes les plus actives, et les emotes les plus utilisées."
        ),
        "chat.no_data": "Aucune donnée de chat disponible pour le moment.",
        "chat.kpi.messages_this_hour": "Messages cette heure",
        "chat.kpi.chatters_this_hour": "Chatteurs uniques cette heure",
        "chat.kpi.total_messages": "Total messages (événement)",
        "chat.chart.activity": "Messages du chat par heure (toutes chaînes)",
        "chat.message_race_heading": "Classement des messages, heure par heure",
        "chat.no_message_race": "Aucun classement de messages par chaîne disponible pour le moment.",
        "chat.message_race_top_n": "Afficher le top N chaînes",
        "chat.message_race_caption": (
            "Les meilleures chaînes au global par messages de chat, heure par heure — "
            "l'historique complet de chaque chaîne sur la période, pas seulement les "
            "heures où elle était en tête."
        ),
        "chat.chart.message_race": "Meilleures chaînes par messages, dans le temps",
        "chat.explain.message_race": (
            "Une ligne par chaîne parmi le top N au global par nombre de messages ; "
            "survolez un point pour son classement exact cette heure-là parmi toutes les "
            "chaînes. Contrairement au volume de messages de l'événement "
            "ci-dessus, ceci montre quelles chaînes précisément étaient les plus actives, "
            "et comment cela a évolué."
        ),
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
        "chat.heatmap_caption": (
            "Un vert plus vif = plus de messages sur cette chaîne, à cette heure ; une "
            "cellule vide signifie que la chaîne n'était simplement pas active cette heure-là."
        ),
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
            "Une cellule par chaîne x heure ; plus c'est vif, plus il y a de messages, et "
            "une cellule vide signifie qu'il n'y a eu aucune activité enregistrée sur cette "
            "chaîne cette heure-là. Utile pour repérer d'un coup d'œil quelles chaînes "
            "étaient actives à quel moment."
        ),
        "chat.spikes_heading": "Pics de chat",
        "chat.no_spikes": "Aucun moment de chat remarquable dans cette plage pour le moment.",
        "chat.spikes_caption": (
            "Les heures où le volume de messages d'une chaîne s'est le plus écarté de sa "
            "propre moyenne."
        ),
        "chat.chart.spikes": "Plus grosses anomalies de volume de messages",
        "chat.spikes_axis": "Écarts-types par rapport à la moyenne de la chaîne",
        "chat.explain.spikes": (
            "Chaque barre est une heure pour une chaîne, notée par rapport à sa propre "
            "moyenne et sa dispersion — une heure ordinaire pour une chaîne habituellement "
            "calme ne dépasse donc pas un moment vraiment inhabituel pour une chaîne plus "
            "active. Rouge/orange marquent les plus extrêmes."
        ),
        "chat.explain.composition": (
            "Les messages de chaque chaîne répartis selon qui les a envoyés (abonné, VIP, "
            "modérateur, viewer simple) — une forte part d'abonnés/modérateurs suggère une "
            "communauté établie, pas seulement du volume brut."
        ),
        "chat.verbosity_heading": "Longueur des messages par chaîne",
        "chat.verbosity_caption": (
            "La longueur type d'un message sur chaque chaîne, en caractères — un chat peut "
            "être à fort volume mais peu élaboré (messages courts, spam d'emotes), ou à "
            "volume plus faible mais plus substantiel."
        ),
        "chat.chart.verbosity": "Longueur moyenne des messages par chaîne",
        "chat.verbosity_axis": "caractères / message",
        "chat.explain.verbosity": (
            "Nombre moyen de caractères par message sur cette chaîne, sur tout l'événement "
            "— un indicateur approximatif de profondeur du chat, pas de sentiment ni de "
            "qualité."
        ),
        "chat.explain.emotes": (
            "Les emotes les plus utilisées de l'événement, par nombre d'utilisations. Les "
            "emotes absentes du catalogue sont affichées avec un identifiant raccourci "
            "plutôt que leur vrai nom (voir la note au-dessus du graphique, le cas échéant)."
        ),
        "chat.emote_search_heading": "Rechercher par emote",
        "chat.emote_search_caption": (
            "Trouvez tous les messages de chat utilisant une emote précise — qui l'a "
            "envoyée, et depuis quelle chaîne."
        ),
        "chat.emote_search_label": 'Code de l\'emote (ex. "Kappa", "LUL")',
        "chat.emote_search_no_matches": "Aucune emote ne correspond à cette recherche.",
        "chat.emote_search_pick": "Laquelle ?",
        "chat.emote_search_no_usage": "Cette emote n'a pas été utilisée dans la plage de dates sélectionnée.",
        "chat.emote_search_results_caption": "{count} messages, les plus récents en premier (limité à 200).",
        "chat.breakdown_heading": "Répartition des messages",
        "chat.breakdown_caption": (
            "Découpez les messages de l'événement par chaîne, chatteur, moment de la "
            "journée, ou emote."
        ),
        "chat.breakdown_dimension": "Répartir par",
        "chat.breakdown.by_channel": "Chaîne",
        "chat.breakdown.by_chatter": "Chatteur",
        "chat.breakdown.by_time": "Moment de la journée",
        "chat.breakdown.by_emote": "Emote",
        "chat.chart.breakdown_channel": "Messages par chaîne",
        "chat.chart.breakdown_chatter": "Messages par chatteur",
        "chat.chart.breakdown_time": "Messages par moment de la journée",
        "chat.chart.breakdown_emote": "Messages par emote",
        "chat.explain.breakdown": (
            "Les 7 plus grosses parts par nombre de messages, plus une seule part "
            "« Autres » pour la traîne — un camembert avec plus de catégories que ça "
            "devient illisible. « Moment de la journée » regroupe chaque message dans "
            "une tranche de 6 heures en heure locale Europe/Paris, quel que soit le "
            "jour de l'événement."
        ),
        "chat.daypart.morning": "Matin (6h-12h)",
        "chat.daypart.afternoon": "Après-midi (12h-18h)",
        "chat.daypart.evening": "Soirée (18h-0h)",
        "chat.daypart.night": "Nuit (0h-6h)",
        "chat.drilldown_heading": "Chatteur ↔ chaîne, en détail",
        "chat.drilldown_caption": (
            "Choisissez un chatteur pour voir ses messages répartis par chaîne, ou une "
            "chaîne pour voir ses messages répartis par chatteur — la même relation, "
            "lue dans chaque sens."
        ),
        "chat.drilldown_chatter_heading": "Un chatteur, par chaîne",
        "chat.drilldown_pick_chatter": "Choisir un chatteur",
        "chat.drilldown_channel_heading": "Une chaîne, par chatteur (inverse)",
        "chat.drilldown_pick_channel": "Choisir une chaîne",
        "chat.chart.drilldown_chatter": "Messages de {chatter} par chaîne",
        "chat.chart.drilldown_channel": "Messages de {channel} par chatteur",
        "chat.explain.drilldown": (
            "À gauche : les messages d'un chatteur, répartis sur chaque chaîne où il a "
            "discuté. À droite : l'inverse — les meilleurs chatteurs d'une chaîne. Le "
            "côté chaîne est approximatif : le classement des chatteurs ne suit qu'une "
            "chaîne (principale) par chatteur, pas toute son activité par chaîne — un "
            "chatteur surtout actif ailleurs mais occasionnellement présent sur cette "
            "chaîne peut donc ne pas apparaître. Seules les chaînes ayant au moins un "
            "chatteur dans le classement sont proposées, pour ne jamais tomber sur un "
            "choix forcément vide."
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
            "plus épais/foncé signifie plus de chatteurs partagés, et la couleur des nœuds "
            "est une communauté détectée (les chaînes dont les audiences se chevauchent le "
            "plus tendent à se regrouper, pas une couleur arbitraire par chaîne). "
            "Choisissez une heure pour voir l'évolution de la structure communautaire ; il "
            "s'ouvre sur la dernière heure avec des données calculées, car l'heure la plus "
            "récente d'un événement en direct peut brièvement accuser un léger retard."
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
            "et la couleur des nœuds est une communauté détectée, comme le graphe heure "
            "par heure ci-dessus. Seuls les plus gros hubs gardent une étiquette "
            "permanente ; survolez un nœud pour son nom."
        ),
        "community.chart.network": "Réseau d'audiences partagées",
        "community.network_min_weight": "Nombre minimum de chatteurs partagés pour afficher un lien",
        "community.network_filtered_caption": (
            "Affichage de {edges} liens sur {total_edges} ({nodes} chaînes sur {total_nodes}) "
            "— augmentez le curseur pour plus de clarté, baissez-le pour voir la longue traîne."
        ),
        "community.weight_picker": "Pondérer les liens par",
        "community.weight.shared_count": "Chatteurs partagés (nombre brut)",
        "community.weight.jaccard": "Indice de Jaccard (recouvrement normalisé)",
        "community.weight.jaccard_caveat": (
            "Indice de Jaccard = chatteurs partagés ÷ chatteurs présents sur *l'une ou "
            "l'autre* chaîne — deux petites chaînes qui partagent l'essentiel de leur "
            "(petite) audience peuvent dépasser deux énormes chaînes avec plus de "
            "chatteurs partagés en valeur absolue mais un recouvrement plus faible "
            "relativement à leur taille. Le nombre brut favorise les grandes chaînes ; "
            "ceci favorise les chaînes très liées, quelle que soit leur taille."
        ),
        "community.weight.shared_count_hover_label": "chatteurs partagés",
        "community.weight.jaccard_hover_label": "recouvrement Jaccard",
        "community.explain.growth": (
            "Le nombre cumulé de chatteurs distincts vus jusqu'à présent, dans le temps — "
            "toujours stable ou croissant."
        ),
        "community.retention_heading": "Rétention des chatteurs, jour par jour",
        "community.no_retention": "Pas encore assez de jours de données pour mesurer la rétention.",
        "community.retention_caption": (
            "Parmi les chatteurs actifs le tout premier jour de l'événement, combien sont "
            "revenus chaque jour suivant — sur tout l'événement, indépendamment du filtre "
            "de date de la barre latérale."
        ),
        "community.retention_day_label": "Jour {day}",
        "community.chart.retention": "Chatteurs du jour 0 encore actifs, par jour",
        "community.retention_live_caveat": (
            "⚠️ Si l'événement est encore en direct, le jour le plus récent affiché est "
            "encore en cours — son chiffre est un minimum, pas un décompte final."
        ),
        "community.explain.retention": (
            "Le « jour » est compté depuis le début de l'événement lui-même (son premier "
            "message), pas l'horloge du calendrier — le jour 0 est les 24 premières "
            "heures pleines, le jour 1 les suivantes, etc. Le pourcentage est la part des "
            "chatteurs du jour 0 encore actifs ce jour-là ; un chatteur parti puis revenu "
            "plus tard compte quand même."
        ),
        "community.new_by_channel_heading": "Nouveaux chatteurs par chaîne",
        "community.no_new_by_channel": "Aucune donnée de nouveaux chatteurs dans cette plage pour le moment.",
        "community.new_by_channel_caption": (
            "Top {shown} chaînes sur {total}, par nouveaux chatteurs attirés."
        ),
        "community.chart.new_by_channel": "Nouveaux chatteurs par chaîne",
        "community.explain.new_by_channel": (
            "Un chatteur compte comme « nouveau pour cette chaîne » la première fois qu'il "
            "y écrit — même un chatteur fidèle ailleurs dans l'événement compte comme "
            "nouveau ici."
        ),
        "community.explain.hourly_network": (
            "Un nœud par chaîne, un lien par paire de chaînes ayant partagé des chatteurs "
            "cette heure-là — plus le lien est épais/foncé, plus de chatteurs sont "
            "partagés. Les nœuds sont colorés par communauté détectée (regroupement par "
            "modularité : quelles chaînes ont des audiences qui se chevauchent plus entre "
            "elles qu'avec le reste) et positionnés près de leur propre cluster, pour que "
            "la structure soit visible d'un coup d'œil plutôt qu'un enchevêtrement "
            "aléatoire. La taille du nœud suit l'audience partagée totale (degré pondéré) ; "
            "seuls les plus gros hubs gardent une étiquette permanente — survolez un nœud "
            "pour son nom, ou un lien pour le nombre exact de chatteurs partagés."
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
            "partage une audience, coloré par communauté détectée et positionné près de "
            "son cluster ; un lien par paire de chaînes, plus épais/foncé pour plus de "
            "chatteurs partagés. À l'échelle de l'événement, contrairement au graphe heure "
            "par heure ci-dessus. Survolez un nœud pour son nom et son degré, ou un lien "
            "pour le nombre exact de chatteurs partagés."
        ),
        "community.migrations_heading": "Passages entre chaînes",
        "community.no_migrations": "Aucune donnée de passages entre chaînes disponible pour le moment.",
        "community.migrations_caption": (
            "À quelle fréquence les chatteurs passent directement d'une chaîne à une autre."
        ),
        "community.chart.migrations": "Migrations de chatteurs entre chaînes",
        "community.explain.migrations": (
            "Un diagramme de flux, pas un graphe de réseau : les migrations sont dirigées "
            "(et une paire de chaînes a souvent des passages dans les deux sens), donc "
            "chaque chaîne apparaît une fois à gauche comme origine et une fois à droite "
            "comme destination. La largeur du ruban suit le nombre de chatteurs ayant fait "
            "ce passage précis — survolez un ruban pour le nombre exact. À l'échelle de "
            "l'événement, non affecté par le filtre de dates de la barre latérale."
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
        "tracker.pick_streamer_single": (
            "Affichage de **{streamer}** — filtré par le filtre streamer de la barre latérale."
        ),
        "tracker.category_filter": "Catégorie d'objectif",
        "tracker.category_filter_help": (
            "Chaque catégorie est suivie comme sa propre chaîne indépendante de "
            "début/fin — en mélanger plusieurs sur la chronologie ci-dessous peut "
            "montrer des périodes d'objectifs sans rapport qui se chevauchent, donc "
            "réduisez à une seule pour une lecture claire."
        ),
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
        "tracker.column.category": "Catégorie",
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
        "chatters.correlation_stat": (
            "r de Pearson = {r} entre chaînes fréquentées et total des messages, sur les "
            "chatteurs affichés (1 = relation linéaire parfaite, 0 = aucune relation linéaire). "
            "Association linéaire uniquement — cela n'implique pas de causalité."
        ),
        "chatters.correlation_stat_na": (
            "Pas assez de chatteurs affichés (ou aucune variation sur un axe) pour calculer "
            "une corrélation."
        ),
        "chatters.lifespan_heading": "Combien de temps les chatteurs restent",
        "chatters.lifespan_caption": (
            "Temps entre le premier et le dernier message d'un chatteur — un indicateur "
            "d'engagement, pas seulement de volume posté."
        ),
        "chatters.chart.lifespan": "Chatteurs par durée d'engagement",
        "chatters.lifespan.single_message": "Message unique",
        "chatters.lifespan.under_1h": "< 1 heure",
        "chatters.lifespan.1_to_6h": "1 - 6 heures",
        "chatters.lifespan.6_to_24h": "6 - 24 heures",
        "chatters.lifespan.24h_plus": "24+ heures",
        "chatters.explain.lifespan": (
            "« Message unique » signifie que le premier et le dernier message sont le "
            "même — typiquement un chatteur de passage, pas forcément un bot (voir "
            "l'heuristique bot ci-dessus pour ça). Les barres de droite sont les chatteurs "
            "revenus sur plusieurs heures, parfois tout l'événement."
        ),
        "chatters.profile_heading": "Profil du chatteur",
        "chatters.pick_chatter": "Choisir un chatteur pour un profil détaillé",
        "chatters.kpi.global_total": "Total des messages (toutes chaînes)",
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
        "chatters.chart.global_bar_label": "Global (toutes chaînes)",
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
        "chatters.by_channel_heading": "Chatteurs d'une chaîne",
        "chatters.by_channel_caption": (
            "Choisissez une chaîne pour voir tous ceux qui y ont discuté — type de badge "
            "(abonné/VIP/modérateur/viewer simple), nombre de messages, première/dernière "
            "activité, et utilisation d'emotes."
        ),
        "chatters.pick_channel": "Choisir une chaîne",
        "chatters.badge_filter": "Filtrer par badge",
        "chatters.kpi.moderators": "Modérateurs",
        "chatters.kpi.subscribers": "Abonnés",
        "chatters.chart.badge_mix": "Messages de {channel} par badge de chatteur",
        "chatters.explain.badge_mix": (
            "Chaque chatteur compte pour exactement un niveau de badge ici (modérateur/"
            "diffuseur > VIP > abonné > viewer simple — l'ordre d'affichage de Twitch "
            "lui-même), selon les badges attachés à ses messages sur cette chaîne, donc les "
            "niveaux ne se chevauchent jamais."
        ),
        "chatters.rank.emotes": "Utilisations d'emotes",
        "chatters.chart.channel_ranked": "Chatteurs de {channel} par {metric}",
        "chatters.explain.channel_ranked": (
            "Le top N des chatteurs de cette chaîne, classés selon la métrique choisie "
            "ci-dessus — total des messages, ou total des utilisations d'emotes (cumulé "
            "sur chaque emote de chaque message, pas seulement les emotes distinctes)."
        ),
        "chatters.by_channel_table_caption": (
            "Une ligne par chatteur, avec ses messages par niveau de badge, sa première/"
            "dernière heure de message, et son utilisation totale d'emotes sur cette chaîne."
        ),
        # --- messages ---
        "messages.title": "Messages du chat",
        "messages.description": (
            "Rechercher et parcourir les messages individuels du chat par date, streamer "
            "et chatteur."
        ),
        "messages.no_data": "Aucune donnée de chat disponible pour le moment.",
        "messages.filters": "Filtres",
        "messages.channel_filter": "Streamer",
        "messages.all_channels": "Tous les streamers",
        "messages.chatter_search": "Le chatteur contient",
        "messages.text_search": "Le message contient",
        "messages.limit_label": "Résultats max",
        "messages.limit_caveat": (
            "Affichage des {limit} messages correspondants les plus récents — affinez les "
            "filtres pour remonter plus loin."
        ),
        "messages.kpi.shown": "Messages affichés",
        "messages.kpi.channels": "Streamers",
        "messages.kpi.chatters": "Chatteurs",
        "messages.time_heading": "Quand ces messages ont eu lieu",
        "messages.time_caption": (
            "Nombre de messages par heure parmi ceux actuellement affichés ci-dessus (après "
            "filtres et limite de résultats) — pas le graphique d'activité globale de la "
            "page Chat en direct."
        ),
        "messages.chart.time": "Messages affichés, dans le temps",
        "messages.explain.time": (
            "Regroupé par heure. Si le nombre de résultats a atteint la limite maximale, "
            "ceci ne couvre que les messages correspondants les plus récents, pas toutes "
            "les correspondances de la période sélectionnée — affinez les filtres pour "
            "remonter plus loin."
        ),
        "messages.breakdown_heading": "Qui et où",
        "messages.breakdown_caption": (
            "Streamers et chatteurs les plus présents parmi les messages actuellement "
            "affichés — même réserve sur la troncature par la limite que le graphique "
            "ci-dessus."
        ),
        "messages.chart.top_channels": "Top streamers, par messages affichés",
        "messages.chart.top_chatters": "Top chatteurs, par messages affichés",
        "messages.explain.breakdown": (
            "Les streamers et chatteurs les plus actifs au sein des résultats de recherche "
            "actuels, pas à l'échelle de l'événement — par exemple, rechercher un mot "
            "précis montre qui le dit le plus, pas qui chatte le plus au global."
        ),
        "messages.table_heading": "Messages",
        "messages.table_caption": "Messages correspondants les plus récents en premier.",
        "messages.column.datetime": "Envoyé à",
        "messages.column.streamer": "Streamer",
        "messages.column.chatter": "Chatteur",
        "messages.column.message": "Message",
        "messages.column.badge": "Badge",
        "messages.chart.badge_mix": "Messages affichés, par badge du chatteur",
        "messages.explain.badge_mix": (
            "Comment les messages actuellement affichés se répartissent entre les badges "
            "modérateur, VIP, abonné et spectateur simple."
        ),
        # --- leaderboard ---
        "leaderboard.title": "Classement",
        "leaderboard.description": (
            "Qui est en tête, au même endroit — meilleurs streamers par dons et audience, "
            "meilleurs chatteurs, et le #1 fan de chaque streamer. Classement sur tout "
            "l'événement, pas une fenêtre glissante."
        ),
        "leaderboard.no_data": "Aucune donnée de streamer disponible pour le moment.",
        "leaderboard.top_n": "Afficher le top N",
        "leaderboard.column.rank": "Rang",
        "leaderboard.column.streamer": "Streamer",
        "leaderboard.column.amount": "Montant",
        "leaderboard.column.chatter": "Chatteur",
        "leaderboard.column.top_fan": "Top fan",
        "leaderboard.column.messages": "Messages",
        "leaderboard.donations_heading": "Meilleurs streamers par dons",
        "leaderboard.donations_caption": (
            "Totaux sur tout l'événement — les mêmes chiffres que le podium de la page Dons "
            "et le classement par dons de la page Streamers, réunis ici."
        ),
        "leaderboard.chart.donations_podium": "Top 3 par dons collectés",
        "leaderboard.explain.donations": (
            "Classé par total de dons collectés, sur tout l'événement, indépendamment du "
            "filtre de date de la barre latérale."
        ),
        "leaderboard.chatters_heading": "Meilleurs chatteurs, sur tout l'événement",
        "leaderboard.chatters_caption": (
            "Les chatteurs les plus actifs sur l'ensemble de l'événement — mêmes chiffres "
            "que le classement de la page Chatteurs, réunis ici."
        ),
        "leaderboard.chart.chatters_podium": "Top 3 par messages envoyés",
        "leaderboard.explain.chatters": (
            "Classé par total de messages envoyés, sur tout l'événement, toutes chaînes "
            "confondues pour chaque chatteur."
        ),
        "leaderboard.fans_heading": "Top fan, par streamer",
        "leaderboard.fans_caption": (
            "Pour chaque streamer, le chatteur ayant posté le plus de messages sur sa "
            "chaîne — introuvable ailleurs dans l'application. Recherchez un streamer par "
            "nom pour le retrouver."
        ),
        "leaderboard.fans_search": "Rechercher par nom de streamer",
        "leaderboard.explain.fans": (
            "Une ligne par streamer : son chatteur le plus actif et le nombre de messages "
            "envoyés là-bas. Le #1 fan d'un streamer n'a pas besoin d'être un chatteur classé "
            "en tête à l'échelle de l'événement — le viewer le plus actif d'un petit streamer "
            "peut très bien dominer ici tout en étant presque invisible ailleurs."
        ),
        "leaderboard.audience_heading": "Meilleurs streamers par audience et efficacité",
        "leaderboard.audience_caption": (
            "Les deux premières métriques reprennent le classement de la page Streamers "
            "(hors dons, couverts ci-dessus) ; les trois métriques d'efficacité sont "
            "nouvelles — des dénominateurs différents (par viewer, par chatteur, par "
            "heure) racontent des histoires différentes sur la conversion d'un stream en "
            "dons. Choisissez-en une pour voir qui est en tête."
        ),
        "leaderboard.metric_picker": "Classer par",
        "leaderboard.metric.viewers": "Audience (viewers moyens)",
        "leaderboard.metric.engagement": "Engagement du chat (messages)",
        "leaderboard.metric.efficiency": "€ par viewer",
        "leaderboard.metric.efficiency_chatters": "€ par chatteur unique",
        "leaderboard.metric.rate": "€ par heure streamée",
        "leaderboard.rate_caveat": (
            "⚠️ Un streamer resté en direct seulement quelques heures peut afficher un taux "
            "extrême à cause d'un seul gros don — c'est un ratio réel, pas un bug, mais un "
            "`hours_live` très court doit inciter à regarder de plus près, pas être pris "
            "comme preuve d'un rythme soutenu."
        ),
        "leaderboard.chart.audience_podium": "Top 3 par {metric}",
        "leaderboard.explain.audience": (
            "Classé selon la métrique choisie ci-dessus — viewers moyens, messages du chat, "
            "dons par viewer ou par chatteur unique (efficacité d'audience, deux "
            "dénominateurs différents — un chatteur est un sous-ensemble plus engagé des "
            "viewers), ou dons par heure réellement streamée (efficacité temporelle, "
            "indépendante de la taille de l'audience)."
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
        # --- about ---
        "about.title": "À propos",
        "about.description": (
            "Ce qu'est ce tableau de bord, d'où viennent ses données, et comment il est "
            "construit."
        ),
        "about.what_heading": "Qu'est-ce que le ZEvent ?",
        "about.what_body": (
            "Le [ZEvent](https://zevent.fr) est un marathon caritatif de streamers "
            "français : des dizaines de streamers Twitch diffusent ensemble pendant une "
            "durée fixe (cette édition : **du 3 au 6 septembre 2026**), et les viewers "
            "font des dons en direct pour une cause choisie avant l'événement. C'est l'un "
            "des plus gros événements de streaming caritatif francophones."
        ),
        "about.dashboard_heading": "Ce que fait ce tableau de bord",
        "about.dashboard_body": (
            "Cette application est une fenêtre en lecture seule sur l'entrepôt de données "
            "de l'événement, mise à jour au fil de l'événement. Elle couvre les dons, la "
            "performance des streamers, les jeux/catégories, les objectifs de dons, le "
            "chat en direct, la communauté des chatteurs, et l'activité par streamer — "
            "neuf pages au total, accessibles depuis la page d'accueil."
        ),
        "about.pipeline_heading": "Comment circulent les données",
        "about.pipeline_body": (
            "Deux pipelines indépendants alimentent l'entrepôt : le site de dons/objectifs "
            "du ZEvent lui-même, et les métadonnées de stream/chat de Twitch — ces "
            "dernières diffusées via [Apache NiFi](https://nifi.apache.org/). Les deux "
            "atterrissent dans le même entrepôt PostgreSQL, modélisé avec "
            "[dbt](https://www.getdbt.com/) sur quatre couches de schéma, chacune "
            "s'appuyant sur la précédente :"
        ),
        "about.pipeline.raw": (
            "Données brutes, telles qu'ingérées — le flux de chat Twitch et les instantanés "
            "du site de dons du ZEvent, exactement tels que capturés."
        ),
        "about.pipeline.stg": (
            "Staging (couche bronze) — les enregistrements bruts normalisés dans une forme "
            "cohérente (types, noms de colonnes) sans en changer le sens."
        ),
        "about.pipeline.int": (
            "Modèles intermédiaires — agrégats par chatteur, par chaîne, par heure, "
            "construits à partir du staging (ex. « messages par chaîne et par heure »)."
        ),
        "about.pipeline.marts": (
            "Marts prêts à l'emploi — les tables que ce tableau de bord lit réellement, une "
            "ou plusieurs par page (ex. le classement des chatteurs, la série temporelle "
            "des dons)."
        ),
        "about.pipeline.column_schema": "Schéma",
        "about.pipeline.column_purpose": "Rôle",
        "about.technical_heading": "Pour data engineers, analystes et ML engineers",
        "about.technical_intro": (
            "Le reste de cette page s'adresse à qui veut la vraie ingénierie "
            "derrière ces graphiques, pas seulement ce qu'ils montrent. Chaque "
            "technique ci-dessous a été choisie et vérifiée sur de vraies "
            "données ZEvent — là où quelque chose n'a pas fonctionné, c'est dit "
            "franchement, pas lissé."
        ),
        "about.technical_dataeng_heading": "Ingénierie des données",
        "about.technical_dataeng_body": (
            "**Interroger une table de 8M+ lignes, sans index, en sécurité.** "
            "`stg.stg_bronze__live_chat` (le flux brut du chat) n'a pas "
            "d'index et grossit en continu pendant l'événement en direct — "
            "toute fonction texte par ligne (correspondance regex, recherche "
            "de chaîne) exécutée directement dessus risque le délai "
            "d'expiration de 15 secondes de l'entrepôt. Chaque requête contre "
            "elle échantillonne d'abord (`WHERE random() < :sample_rate`), "
            "*puis* n'exécute le travail coûteux par ligne que sur "
            "l'échantillon — réduisant le nombre de lignes avant la partie "
            "coûteuse, pas après.\n\n"
            "**Lectures à un instant T sous un événement en direct.** "
            "Plusieurs graphiques (l'instantané de prévision des dons, les "
            "mouvements du classement, les classements en série temporelle "
            "par chaîne) ont besoin de « la valeur la plus récente à un "
            "instant passé », pas juste « la valeur actuelle » — implémenté "
            "via `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ingested_at "
            "DESC)` filtré à `rn = 1`, restreint aux lignes à ou avant "
            "l'instant choisi.\n\n"
            "**Mise en cache, échelonnée selon la vitesse réelle de "
            "changement des données.** Les requêtes de l'événement en direct "
            "sont mises en cache 60 secondes (`st.cache_data(ttl=60)`) ; les "
            "statistiques du catalogue de la base (section ci-dessus) sont "
            "mises en cache 5 minutes — elles changent bien plus lentement "
            "que les chiffres de l'événement, donc un TTL court ne ferait que "
            "relancer le même scan de catalogue pour la même réponse ; "
            "l'historique des éditions passées (récupéré en externe, figé "
            "pour toujours) est mis en cache sans aucun TTL. Un `Engine` "
            "SQLAlchemy mutualisé et borné (`st.cache_resource`) est partagé "
            "entre toutes les sessions concurrentes plutôt qu'une connexion "
            "par visiteur."
        ),
        "about.technical_stats_heading": "Analyse statistique et heuristique (Chat Intelligence)",
        "about.technical_stats_body": (
            "Chat Intelligence est délibérément léger en dépendances : "
            "correspondance de listes de mots et comptage, pas de modèle "
            "entraîné. Chaque liste de mots a été testée sur de vrais "
            "messages avant d'être conservée — plusieurs premières "
            "suppositions intuitives pour une liste d'hostilité (« con », "
            "« stupide », « pourri ») ont été essayées puis rejetées car les "
            "données réelles montraient qu'elles touchaient surtout autre "
            "chose (un titre de jeu, un code d'emote Twitch, de l'argot "
            "inoffensif). La correspondance utilise une limite de mot "
            "*seulement en tête* (l'ancre `\\y` de Postgres, d'un seul côté), "
            "ni une simple sous-chaîne ni une limite des deux côtés — "
            "vérifié comme étant le seul réglage qui évite les faux positifs "
            "de codes d'emotes (`\"melokaIdiot\"`) sans pour autant perdre de "
            "vrais pluriels et des formes allongées par emphase "
            "(`\"connards\"`, `\"CONNASSEEEE\"`) comme faux négatifs."
        ),
        "about.technical_ml_heading": "Vrai apprentissage automatique (Chat ML Lab)",
        "about.technical_ml_body": (
            "**Clustering** (`sklearn.cluster.KMeans`) segmente à la fois les "
            "sujets de messages (chat regroupé par heure-chaîne, TF-IDF sur "
            "des unigrammes+bigrammes lemmatisés) et le comportement des "
            "streamers/chatteurs (variables de forme de performance et "
            "d'activité, transformées en log1p puis standardisées — les "
            "vrais chiffres de dons/activité sont fortement asymétriques, "
            "vérifié sur données réelles). Une projection ACP en 2D du même "
            "espace de variables sur lequel le clustering a été ajusté rend "
            "ces segments réellement *visibles*, pas seulement tabulés.\n\n"
            "**Détection d'anomalies** (`sklearn.ensemble.IsolationForest`) "
            "signale les streamers, chatteurs et heures d'ambiance de chat "
            "dont la forme est statistiquement inhabituelle — vérifié pour "
            "faire remonter les deux extrêmes à la fois (les plus gros "
            "collecteurs de fonds de l'événement *et* les entrées "
            "quasi-inactives), avec la fraction d'anomalies attendue exposée "
            "comme curseur ajustable.\n\n"
            "**Prévision des dons** (`sklearn.ensemble.RandomForestRegressor`) "
            "prédit le total final de dons d'un streamer à partir d'un "
            "instantané de ses propres dons/viewers/messages à un instant "
            "antérieur réel — délibérément pas à partir de ses propres "
            "statistiques finales, ce qui serait quasi tautologique. Évalué "
            "honnêtement sur un jeu de test de 25 % mis de côté, pas sur les "
            "données d'entraînement.\n\n"
            "**Classification par transformer pré-entraîné** (`transformers`) "
            "compare de vrais modèles de sentiment/toxicité à l'heuristique "
            "par liste de mots ci-dessus. Le choix du modèle a été vérifié, "
            "pas supposé : un modèle de toxicité multilingue plus petit a "
            "classé avec confiance un message bienveillant comme toxique à "
            "99 % et manqué une véritable insulte, avant d'être remplacé par "
            "un modèle qui a obtenu tous les vrais messages de test "
            "correctement.\n\n"
            "**Analyse linguistique** (pipeline français de spaCy) ajoute la "
            "lemmatisation, l'étiquetage grammatical, l'analyse syntaxique en "
            "dépendances, la reconnaissance d'entités nommées, et des "
            "plongements de mots/messages à la fois statiques (façon "
            "word2vec/GloVe) et contextuels (dérivés d'un transformer). La "
            "NER est la seule technique ici avec un vrai point faible sur ce "
            "texte : un modèle français généraliste, entraîné sur de "
            "l'écriture formelle, continue de lire certains codes d'emotes "
            "Twitch et argot de chat comme de vraies entités même après "
            "filtrage — dit dans la page elle-même, pas caché."
        ),
        "about.technical_principles_heading": "Principes de travail",
        "about.technical_principles_body": (
            "1. **Vérifier sur de vraies données avant de livrer, pas "
            "seulement sur la documentation.** Plusieurs techniques "
            "ci-dessus ont été essayées, jugées insuffisantes sur du vrai "
            "chat ZEvent, puis remplacées ou filtrées — c'est le chemin "
            "normal, pas une exception.\n"
            "2. **Énoncer les vraies limites d'un modèle dans l'interface "
            "elle-même.** Un signalement de toxicité, une entité NER ou une "
            "prévision est une piste à examiner en contexte, jamais présentée "
            "comme un verdict certifié.\n"
            "3. **Concevoir pour éliminer la circularité.** Une prévision "
            "prédit une valeur réellement *future* à partir d'un instantané "
            "réellement *passé* — jamais un nombre à partir d'une "
            "reformulation de lui-même.\n"
            "4. **Respecter les vraies contraintes de la base de données.** "
            "Échantillonner avant le travail coûteux par ligne, pas après ; "
            "un délai d'expiration de 15 secondes est un budget strict, pas "
            "une suggestion."
        ),
        "about.infra_heading": "Infrastructure & supervision",
        "about.infra_body": (
            "Le pipeline et son hébergement sont provisionnés en code "
            "(infrastructure as code), pas configurés à la main. "
            "[Prometheus](https://prometheus.io/) et [Grafana](https://grafana.com/) "
            "supervisent le pipeline et l'entrepôt (retard d'ingestion, échecs de job, "
            "fraîcheur des tables), et [ntfy](https://ntfy.sh/) envoie des alertes quand "
            "quelque chose nécessite attention — ce tableau de bord est un consommateur "
            "en lecture seule de l'entrepôt que ces alertes protègent, il ne fait pas "
            "partie de la chaîne d'alerte elle-même."
        ),
        "about.freshness_heading": "Fraîcheur des données",
        "about.freshness_body": (
            "Chaque requête de page est mise en cache 60 secondes, donc les chiffres "
            "affichés peuvent avoir jusqu'à une minute de retard sur l'événement en "
            "direct. Comme il s'agit d'un événement *en direct*, certains marts ont "
            "besoin qu'une heure soit entièrement terminée avant d'être calculés pour "
            "elle — le cas le plus visible : l'heure la plus récente du réseau de la "
            "communauté des chatteurs peut brièvement n'afficher aucune donnée le temps "
            "que le pipeline de cette heure se termine. Ce tableau de bord sélectionne "
            "par défaut la dernière heure qui a déjà des données, donc vous ne devriez "
            "normalement pas le voir — mais c'est pour ça que le sélecteur d'heure peut "
            "quand même tomber sur une heure vide si vous allez tout au bord."
        ),
        "about.privacy_heading": "Confidentialité",
        "about.privacy_body": (
            "Les pseudos Twitch sont réels et affichés à l'écran, comme ils apparaîtraient "
            "dans la chaîne elle-même. Tout export CSV incluant un identifiant de chatteur "
            "le remplace d'abord par un pseudonyme à sens unique (voir la page Chatteurs), "
            "donc un fichier téléchargé ne peut jamais être retracé jusqu'à une personne "
            "réelle."
        ),
        "about.stack_heading": "Construit avec",
        "about.stack_body": (
            "[Streamlit](https://streamlit.io) pour l'application elle-même, "
            "[Polars](https://pola.rs) pour toutes les transformations, "
            "[Plotly](https://plotly.com/python/) pour les graphiques, "
            "[dbt](https://www.getdbt.com/) + PostgreSQL pour l'entrepôt, le tout en "
            "Python."
        ),
        "about.related_heading": "Projets liés",
        "about.related_body": (
            "Cette application fait partie d'un petit écosystème : `zevent-analysis` "
            "(analyse hors-ligne plus poussée), `zevent-db` (l'entrepôt que lit cette "
            "application), et `zevent-infra-monitoring` (supervision pipeline/infra). Ce "
            "tableau de bord est actuellement le seul des quatre avec un livrable "
            "fonctionnel."
        ),
        # --- chat intelligence ---
        "chatintel.title": "Intelligence du chat",
        "chatintel.description": (
            "Analyse légère du texte du chat, sans données d'entraînement : quelles "
            "chaînes ont le chat le plus \"hype\", positif ou hostile ; quels messages "
            "sont copiés-collés en masse ; et quels mots deviennent tendance dans le chat "
            "d'une chaîne au fil du temps. Voir « Comment ces mesures sont calculées » "
            "ci-dessous pour la méthodologie exacte."
        ),
        "chatintel.methodology_heading": "Comment ces mesures sont calculées",
        "chatintel.methodology_intro": (
            "Chaque mesure ci-dessous est une heuristique/liste de mots — compter des "
            "mots et des motifs — pas un modèle de machine learning entraîné. C'est "
            "volontaire, pas un raccourci : le vrai chat de ZEvent est court, en "
            "français, riche en emotes, et non étiqueté, et une simple regex sur la "
            "table sous-jacente d'environ 7,7 millions de messages dépasse "
            "systématiquement le délai à cette échelle (voir « Échantillonnage » plus "
            "bas). Dans chaque formule, $p_x$ signifie « la fraction des messages "
            "échantillonnés qui remplissent la condition $x$ »."
        ),
        "chatintel.methodology_hype_intro": (
            "Score de hype (0-100) — un mélange de ponctuation abondante, de messages "
            "TOUT EN MAJUSCULES, et de mentions d'emotes hype, pondérés 40/30/30 :"
        ),
        "chatintel.methodology_hype_terms": (
            "p_punct = messages contenant \"!!\" ou plus · p_caps = message entier en "
            "MAJUSCULES avec au moins 4 lettres · p_emote = messages mentionnant une "
            "emote hype connue."
        ),
        "chatintel.methodology_hype_tunable": (
            "Les poids (w) valent 0,4/0,3/0,3 par défaut mais sont réglables — voir les "
            "curseurs dans la section Baromètre de hype du chat ci-dessous."
        ),
        "chatintel.methodology_sentiment_intro": (
            "Score de sentiment (-100 à +100) — taux de mots positifs moins taux de "
            "mots hostiles :"
        ),
        "chatintel.methodology_toxicity_intro": (
            "Score de toxicité (0-100) — ce même taux de mots hostiles seul :"
        ),
        "chatintel.methodology_words_intro": (
            "Les listes de mots exactement utilisées actuellement — chaque mot a été "
            "testé individuellement sur le vrai chat avant d'être gardé ; plusieurs "
            "choix intuitifs (\"con\", \"cretin\", \"stupide\", \"pourri\") ont échoué et "
            "ont été écartés, voir ci-dessous. La correspondance exige aussi une "
            "limite de mot juste avant le mot (pas une simple sous-chaîne) : un audit "
            "sur des données réelles a montré que \"idiot\" en simple sous-chaîne "
            "correspondait aussi à des codes d'emotes Twitch (\"melokaIdiot\") et au "
            "pseudo réel de quelqu'un simplement mentionné (\"@je_un_idiot\") — une "
            "limite de mot écarte les deux, tout en gardant les pluriels et les "
            "formes allongées par emphase (\"connards\", \"CONNASSEEEE\") qu'une "
            "limite *plus stricte* des deux côtés aurait manquées."
        ),
        "chatintel.methodology_positive_words_label": "Mots positifs :",
        "chatintel.methodology_hype_emote_words_label": "Mots d'emotes hype :",
        "chatintel.methodology_hostile_words_label": "Mots hostiles :",
        "chatintel.methodology_examples_pointer": (
            "Curieux de savoir ce qui compte vraiment comme \"hostile\" ? Ouvrez "
            "« Voir des exemples de messages signalés » sous Toxicité du chat "
            "ci-dessous pour vérifier vous-même de vraies correspondances."
        ),
        "chatintel.methodology_keywords_intro": (
            "Mots-clés tendance — TF-IDF sur les messages d'une chaîne, en regroupant "
            "tout le texte d'une heure en un seul « document » :"
        ),
        "chatintel.methodology_keywords_terms": (
            "N_hours = nombre total d'heures dans l'historique de la chaîne · df(w) = "
            "nombre d'heures où le mot w apparaît au moins une fois."
        ),
        "chatintel.methodology_phrases_intro": (
            "Phrases tendance — aucune formule nécessaire : le même message (en "
            "minuscules, espaces retirés) envoyé au moins 5 fois en une heure sur "
            "une chaîne, compté directement."
        ),
        "chatintel.methodology_correlation_intro": (
            "Ambiance du chat vs rythme des dons — le coefficient de corrélation de "
            "Pearson standard entre le score d'ambiance horaire au global et le "
            "rythme des dons de cette même heure :"
        ),
        "chatintel.methodology_sampling_intro": (
            "Échantillonnage — chaque mesure à l'échelle de l'événement ci-dessus "
            "(hype, sentiment, toxicité, phrases tendance) tourne sur un échantillon "
            "aléatoire dimensionné pour rester rapide, pas sur tous les messages :"
        ),
        "chatintel.methodology_sampling_terms": (
            "N_target = 250 000 messages (300 000 pour les phrases tendance) · "
            "N_total = messages dans la fenêtre sélectionnée. Une fenêtre déjà plus "
            "petite que la cible utilise tous les messages (sample_rate = 1)."
        ),
        "chatintel.methodology_toxicity_privacy": (
            "Le *score* de toxicité ci-dessus est une tendance au niveau de la "
            "chaîne volontairement — il s'agit de savoir quelles chaînes chauffent, "
            "pas de pointer un chatteur en particulier. Les messages d'exemple "
            "ci-dessous, et les outils de toxicité du ML Lab, affichent bien le vrai "
            "chatteur ayant envoyé un message signalé (comme toutes les autres pages "
            "listant des chatteurs dans cette application) — mais l'heuristique se "
            "trompe encore parfois (voir la liste de mots ci-dessus et ses faux "
            "positifs connus), donc traitez un signalement comme quelque chose à "
            "vérifier en contexte, pas comme un verdict sur la personne."
        ),
        "chatintel.no_streamers": "Aucune donnée de streamer disponible pour le moment.",
        "chatintel.hype_heading": "Baromètre de hype du chat",
        "chatintel.hype_weight_punct": "Poids ponctuation",
        "chatintel.hype_weight_caps": "Poids MAJUSCULES",
        "chatintel.hype_weight_emote": "Poids emotes hype",
        "chatintel.hype_top_n": "Afficher le top N chaînes",
        "chatintel.hype_caption": (
            "Les meilleures chaînes au global par \"hype\" du chat — un mélange "
            "heuristique de messages riches en points d'exclamation, de messages "
            "TOUT EN MAJUSCULES et de mentions d'emotes hype, pas le volume brut de "
            "messages. Une petite communauté plus excitable peut dépasser une bien plus "
            "grande mais plus calme. Faites glisser les trois curseurs ci-dessous pour "
            "changer le poids de chaque signal — le graphique se recalcule instantanément, "
            "sans recharger la page."
        ),
        "chatintel.chart.hype": "Score de hype du chat, dans le temps",
        "chatintel.unit.hype_score": "score de hype",
        "chatintel.no_hype": "Aucune donnée de hype disponible pour le moment.",
        "chatintel.explain.hype": (
            "Le score de hype (0-100) combine trois signaux par message, moyennés par "
            "heure : ponctuation \"!!\" ou plus, messages TOUT EN MAJUSCULES, et mentions "
            "d'emotes hype connues (LUL, KEKW, PogChamp, ...) — pondérés selon les trois "
            "curseurs ci-dessus (0,4/0,3/0,3 par défaut). Les trois taux bruts sont "
            "récupérés une seule fois par plage de dates et la pondération est recalculée "
            "dans le navigateur, donc déplacer un curseur ne relance jamais de requête "
            "vers la base de données. Calculé sur un échantillon aléatoire des messages "
            "de l'heure (les heures avec trop peu de messages échantillonnés sont "
            "ignorées) plutôt qu'un scan complet, une analyse message par message sur "
            "tout l'événement étant trop lente à la demande. Survolez un point pour son "
            "classement exact cette heure-là parmi toutes les chaînes."
        ),
        "chatintel.sentiment_heading": "Sentiment du chat",
        "chatintel.sentiment_top_n": "Afficher le top N chaînes",
        "chatintel.sentiment_caption": (
            "Les chaînes les plus positives au global, heure par heure — taux de mots "
            "positifs moins taux de mots hostiles. Ce n'est pas la même chose que la "
            "hype ci-dessus : une chaîne peut être très positive sans être bruyante, ou "
            "bruyante sans être particulièrement positive."
        ),
        "chatintel.chart.sentiment": "Score de sentiment du chat, dans le temps",
        "chatintel.unit.sentiment_score": "score de sentiment",
        "chatintel.no_sentiment": "Aucune donnée de sentiment disponible pour le moment.",
        "chatintel.explain.sentiment": (
            "Le score de sentiment (-100 à +100) est un taux de mots positifs "
            "sélectionnés (\"merci\", \"super\", \"bravo\", \"excellent\", ...) moins le "
            "même taux de mots hostiles utilisé par la toxicité (ci-dessous), moyenné "
            "par heure, calculé de la même façon échantillonnée que la hype (voir "
            "« Comment ces mesures sont calculées » ci-dessus). Survolez un point pour "
            "son classement exact cette heure-là parmi toutes les chaînes."
        ),
        "chatintel.toxicity_heading": "Toxicité du chat",
        "chatintel.toxicity_top_n": "Afficher le top N chaînes",
        "chatintel.toxicity_caption": (
            "Les chaînes les plus hostiles au global, heure par heure — comment le "
            "langage le plus négatif du chat se déplace entre les chaînes au fil de "
            "l'événement. Ceci suit des *chaînes*, pas des chatteurs : aucun chatteur "
            "n'est jamais nommé ou signalé comme \"toxique\" ici, volontairement (voir "
            "« Comment ces mesures sont calculées » ci-dessus)."
        ),
        "chatintel.chart.toxicity": "Score de toxicité du chat, dans le temps",
        "chatintel.unit.toxicity_score": "score de toxicité",
        "chatintel.no_toxicity": "Aucune donnée de toxicité disponible pour le moment.",
        "chatintel.explain.toxicity": (
            "Le score de toxicité (0-100) est un taux de mots hostiles sélectionnés "
            "(\"connard\", \"idiot\", \"dégage\", \"ta gueule\", ...), moyenné par heure, "
            "calculé de la même façon échantillonnée que la hype (voir « Comment ces "
            "mesures sont calculées » ci-dessus). Il mesure une densité de langage "
            "hostile, pas un classificateur certifié de harcèlement/discours haineux — "
            "il manquera les insultes et propos hostiles qui évitent ces mots précis, et "
            "ne peut pas distinguer une insulte ciblée d'une taquinerie entre amis. "
            "Survolez un point pour son classement exact cette heure-là parmi toutes les "
            "chaînes."
        ),
        "chatintel.toxicity_examples_heading": "Voir des exemples de messages signalés",
        "chatintel.toxicity_examples_caption": (
            "Un échantillon aléatoire de messages correspondant à la liste de mots "
            "hostiles ci-dessus dans la fenêtre sélectionnée — vérifiez vous-même le "
            "travail de l'heuristique. Affiche la vraie chaîne et le vrai chatteur, "
            "comme les pages Chatteurs/Streamers/Communauté — mais la liste de mots "
            "se trompe encore parfois (voir la mise en garde sur les faux positifs "
            "ci-dessus), donc traitez une correspondance ici comme une piste à "
            "regarder, pas comme un verdict."
        ),
        "chatintel.no_toxicity_examples": (
            "Aucun message signalé dans la plage sélectionnée pour le moment."
        ),
        "chatintel.column.chatter": "Chatteur",
        "chatintel.column.message": "Message",
        "chatintel.correlation_heading": "Ambiance du chat vs rythme des dons",
        "chatintel.correlation_caption": (
            "L'excitation ou la positivité du chat suit-elle vraiment le montant des "
            "dons ? La hype et le sentiment sont ici moyennés sur toutes les chaînes "
            "chaque heure, pas seulement le top N — une seule ambiance globale par "
            "heure, comparée au rythme des dons de cette même heure."
        ),
        "chatintel.no_correlation": (
            "Pas assez d'heures en commun pour calculer une corrélation pour le moment."
        ),
        "chatintel.correlation_summary": (
            "Sur {n} heures : la hype est corrélée à r = {hype_corr} avec le rythme des "
            "dons ; le sentiment est corrélé à r = {sentiment_corr}. Un coefficient "
            "proche de 0 signifie aucune relation, proche de +1/-1 une relation forte — "
            "avec seulement quelques dizaines d'heures, considérez ceci comme un signal "
            "approximatif, pas une mesure précise, et rappelez-vous que corrélation "
            "n'est pas causalité."
        ),
        "chatintel.chart.correlation": "Hype du chat vs rythme des dons, un point par heure",
        "chatintel.explain.correlation": (
            "Chaque point est une heure : son score de hype moyen au global (axe X) "
            "contre le montant donné cette heure-là (axe Y). Un nuage de points qui "
            "monte de gauche à droite suggère que la hype et les dons évoluent "
            "ensemble cette heure-là ; un nuage plat ou dispersé suggère le contraire. "
            "Calculé à partir de `chat_mood_timeseries` (même échantillonnage que la "
            "hype/le sentiment ci-dessus) rapproché du rythme horaire propre à la page "
            "des dons."
        ),
        "chatintel.phrases_heading": "Phrases tendance & copypasta",
        "chatintel.phrases_top_n": "Afficher le top N phrases",
        "chatintel.phrases_caption": (
            "Les messages exacts (normalisés en casse/espaces) les plus répétés au sein "
            "d'une même heure sur une même chaîne, tous canaux confondus — le classique "
            "\"copypasta\" du chat Twitch : la même ligne spammée par de nombreux "
            "chatteurs en rafale."
        ),
        "chatintel.no_phrases": "Aucune phrase répétée trouvée pour le moment.",
        "chatintel.column.hour": "Heure",
        "chatintel.column.channel": "Chaîne",
        "chatintel.column.phrase": "Phrase",
        "chatintel.column.repeat_count": "Répétitions",
        "chatintel.explain.phrases": (
            "Compté sur un échantillon aléatoire des messages de chaque heure, pas un "
            "scan complet (même raison que le baromètre de hype ci-dessus) — les vrais "
            "nombres de répétitions sont plus élevés que ceux affichés. Seules les "
            "phrases répétées au moins 5 fois dans l'heure échantillonnée sont gardées, "
            "pour filtrer les messages courts que deux chatteurs auraient envoyés une "
            "fois chacun par coïncidence."
        ),
        "chatintel.keywords_heading": "Mots tendance par chaîne",
        "chatintel.pick_channel": "Choisir une chaîne",
        "chatintel.keywords_caption": (
            "Les mots les plus distinctifs du chat d'une chaîne, heure par heure — un mot "
            "qui explose soudainement pendant une heure (un shoutout, une blague "
            "récurrente, la révélation d'un objectif de dons) ressort devant des mots "
            "utilisés à un rythme faible mais constant."
        ),
        "chatintel.no_keywords": "Aucune donnée de chat disponible pour cette chaîne pour le moment.",
        "chatintel.column.keywords": "Mots-clés principaux",
        "chatintel.explain.keywords": (
            "Utilise tous les messages de la chaîne sélectionnée (pas d'échantillonnage "
            "nécessaire — récupérer tous les messages d'une seule chaîne reste bon "
            "marché). Les mots de chaque heure sont notés par TF-IDF : leur fréquence "
            "cette heure-là, pondérée à la hausse selon leur rareté sur les autres heures "
            "de la chaîne — la même statistique utilisée par les moteurs de recherche "
            "pour distinguer un mot distinctif d'un mot courant. Aucun modèle de "
            "sentiment ou de sujet n'est utilisé."
        ),
        # --- chat ml lab ---
        "chatml.title": "Chat ML Lab",
        "chatml.description": (
            "De vrais modèles de machine learning entraînés sur le chat en direct — "
            "plus lourds et plus lents que les heuristiques à base de mots "
            "d'Intelligence du chat, pour des questions que celles-ci ne peuvent pas "
            "résoudre : quels sujets le chat découvre-t-il réellement, quels segments "
            "comportementaux existent parmi les chatteurs, et un vrai modèle est-il "
            "seulement d'accord avec la liste de mots ?"
        ),
        "chatml.topics_heading": "Clusters de sujets des messages",
        "chatml.topics_caption": (
            "Un vrai clustering non supervisé (K-Means sur TF-IDF), pas un classement "
            "de mots-clés — chaque heure de chat d'une chaîne est regroupée en un seul "
            "« document » et rapprochée des heures similaires sur tout l'événement, "
            "découvrant de vrais sujets (un moment de vote façon Twitch-plays, le "
            "bavardage riche en emotes propre à une chaîne, des discussions sur les "
            "objectifs de dons, ...) plutôt que de simplement compter des mots."
        ),
        "chatml.topics_n_clusters": "Nombre de clusters de sujets",
        "chatml.no_topics": (
            "Pas assez de messages dans la plage sélectionnée pour former des clusters "
            "de sujets pour le moment."
        ),
        "chatml.chart.topics": "Taille des clusters de sujets (heures-chaîne)",
        "chatml.column.cluster": "Cluster",
        "chatml.column.channel_hours": "Heures-chaîne",
        "chatml.column.top_terms": "Termes principaux",
        "chatml.explain.topics": (
            "Chaque heure-chaîne avec assez de messages échantillonnés devient un "
            "« document » TF-IDF ; K-Means regroupe les documents similaires entre "
            "eux. Les « termes principaux » d'un cluster sont les mots qui définissent "
            "le plus son centroïde — pas forcément son mot le plus fréquent, mais les "
            "mots qui le distinguent le plus de tous les autres clusters. Le "
            "clustering des messages individuels bruts a été essayé en premier puis "
            "écarté : les vrais messages de chat sont si courts que presque tous se "
            "retrouvaient dans un seul cluster fourre-tout sans intérêt ; regrouper "
            "d'abord par heure-chaîne corrige cela.\n\n"
            "Les mots sont lemmatisés avant le comptage (pipeline français de "
            "spaCy) — « joue »/« jouait »/« jouer » fusionnent en un seul terme "
            "partagé au lieu de diviser le signal d'un sujet entre ses formes "
            "fléchies — et un terme « mot mot » (joint par un espace ici, par un "
            "underscore en interne) est un bigramme : deux mots comptés comme une "
            "seule expression, pas deux occurrences séparées. Les codes d'emotes "
            "Twitch et le spam de copier-coller sont filtrés avant le comptage "
            "(voir la section Analyse linguistique ci-dessous pour savoir "
            "exactement comment, et où ce filtrage laisse encore passer du bruit)."
        ),
        "chatml.linguistics_heading": "Analyse linguistique (NLP)",
        "chatml.linguistics_caption": (
            "Structure linguistique réelle sur un échantillon de texte de chat, "
            "via le pipeline français de spaCy (`fr_core_news_md`) et l'encodeur "
            "propre au modèle de toxicité — étiquetage grammatical (POS), analyse "
            "syntaxique en dépendances, reconnaissance d'entités nommées, "
            "plongements de mots statiques, et plongements contextuels de "
            "messages. Chaque technique ici a été testée sur de vraies données "
            "ZEvent avant d'être conservée — voir le « Comment lire ce graphique » "
            "de chaque sous-section pour ce qui a fonctionné et, honnêtement, ce "
            "qui n'a pas fonctionné."
        ),
        "chatml.no_linguistics": (
            "Pas assez de messages dans la plage sélectionnée pour lancer "
            "l'analyse linguistique."
        ),
        "chatml.pos_heading": "Répartition grammaticale (POS)",
        "chatml.column.pos": "Étiquette POS",
        "chatml.column.count": "Nombre",
        "chatml.chart.pos_distribution": "Fréquence de chaque rôle grammatical dans le chat",
        "chatml.explain.pos": (
            "Étiquettes POS universelles (jeu d'étiquettes de spaCy) : "
            "`NOUN`/`PROPN` (noms communs/propres), `VERB`, `ADJ`, `ADV`, `PRON` "
            "(pronoms), `DET` (déterminants — « le »/« la »/« un »), `ADP` "
            "(prépositions — « de »/« pour »), `INTJ` (interjections), `PUNCT`. "
            "Un chat dominé par des réactions courtes et des interjections plutôt "
            "que des phrases complètes se traduit ici par un déséquilibre réel et "
            "mesurable vers `INTJ`/`PUNCT`/`PRON` par rapport au français écrit "
            "formel — pas seulement une impression tirée de la lecture de "
            "quelques messages."
        ),
        "chatml.ner_heading": "Entités nommées mentionnées",
        "chatml.column.entity": "Entité",
        "chatml.column.label": "Type",
        "chatml.chart.entities": "Entités nommées les plus fréquemment mentionnées",
        "chatml.explain.ner": (
            "**Limite honnête, pas cachée.** C'est un modèle français de "
            "reconnaissance d'entités généraliste — entraîné sur du texte écrit "
            "formel, pas sur le chat Twitch — et il continuera de lire certains "
            "codes d'emotes et argot de chat comme de vraies entités même après "
            "filtrage (vérifié sur de vraies données ZEvent : « MegaphoneZ », une "
            "emote de train de hype, a été lu comme une personne plus de 200 fois "
            "avant l'ajout d'un filtre de code d'emote ; certain bruit, comme "
            "les cris en majuscules ou les codes d'emotes sans majuscule "
            "intérieure, passe encore). Le filtre retire le texte avec une "
            "majuscule en milieu de mot (`\"MegaphoneZ\"`, `\"adfaceBZZZ\"` — un "
            "vrai nom propre ne capitalise jamais que sa première lettre), le "
            "spam de lettres répétées (`\"MDRRR\"`), et une courte liste "
            "d'interjections de chat courantes. Ce qui survit — `PER` "
            "(personne), `LOC` (lieu), `ORG` (organisation), `MISC` — tend vers "
            "du vrai signal (noms de streamers, titres de jeux) d'autant plus "
            "qu'une mention revient souvent, une erreur de classification isolée "
            "revenant rarement aussi souvent qu'une entité réellement discutée."
        ),
        "chatml.parse_heading": "Analyse syntaxique en dépendances",
        "chatml.parse_input_label": "Message à analyser",
        "chatml.parse_caption": (
            "Le rôle grammatical de chaque mot et ce dont il dépend — la "
            "structure qu'un lecteur utilise pour analyser une phrase sans y "
            "penser, rendue explicite. Essayez de coller un vrai message de "
            "chat, en français ou en anglais."
        ),
        "chatml.column.token": "Token",
        "chatml.column.lemma": "Lemme",
        "chatml.column.dependency": "Dépendance",
        "chatml.column.head": "Dépend de",
        "chatml.explain.parse": (
            "`dependency` est la relation grammaticale du token avec son `head` "
            "— par ex. `nsubj` (sujet nominal), `amod` (modifieur adjectival), "
            "`det` (déterminant), `ROOT` (le verbe/prédicat principal de la "
            "phrase, qui ne dépend de rien — son propre `head` est lui-même). "
            "Lire `head` pour chaque ligne reconstruit tout l'arbre de "
            "dépendances de la phrase sans avoir besoin d'un diagramme : suivre "
            "chaque mot jusqu'à ce qu'il modifie, jusqu'au `ROOT`."
        ),
        "chatml.word_embeddings_heading": (
            "Plongements de mots : une carte sémantique du vocabulaire du chat"
        ),
        "chatml.chart.word_embeddings": (
            "Mots de contenu fréquents, projetés par sens (ACP des vecteurs de mots)"
        ),
        "chatml.explain.word_embeddings": (
            "Chaque mot reçoit un vecteur fixe à 300 dimensions issu de la table "
            "de plongements de mots statiques de spaCy (entraînée sur du "
            "français général, pas ce chat), projeté ici en 2D — les mots que le "
            "modèle considère proches en sens ou en usage se retrouvent proches "
            "les uns des autres, indépendamment de tout ce qui est spécifique à "
            "ZEvent. « Statique » est le mot-clé : contrairement aux plongements "
            "contextuels ci-dessous, un mot a exactement un vecteur peu importe "
            "le message dans lequel il apparaît — c'est le sens classique de "
            "« plongement de mots » (façon word2vec/GloVe), une table fixe "
            "unique, pas une représentation entraînée par contexte."
        ),
        "chatml.contextual_embeddings_heading": (
            "Plongements contextuels : le même mot, des sens différents"
        ),
        "chatml.contextual_embeddings_caption": (
            "Contrairement aux vecteurs de mots statiques ci-dessus, un "
            "plongement contextuel dépend de la *phrase* dans laquelle se "
            "trouve un mot, pas seulement du mot lui-même — le même mot peut se "
            "retrouver à un endroit différent selon ce qui l'entoure. Réutilise "
            "l'encodeur propre du classificateur de toxicité purement comme "
            "encodeur de texte multilingue généraliste (sa tête de "
            "classification n'est pas utilisée ici) — un vecteur à 768 "
            "dimensions par message, moyenné sur les positions de tokens réels "
            "(hors remplissage), puis projeté en 2D. Caché derrière un bouton, "
            "même raison que la section de classification ML : cela charge un "
            "grand modèle transformer, non exécuté automatiquement."
        ),
        "chatml.contextual_embeddings_button": "Calculer les plongements contextuels",
        "chatml.contextual_embeddings_hint": (
            "Cliquez sur « Calculer les plongements contextuels » ci-dessus pour "
            "charger le modèle et voir une carte 2D de vrais messages — non "
            "exécuté automatiquement, car cela peut télécharger environ 2 Go la "
            "première fois."
        ),
        "chatml.contextual_embeddings_spinner": "Calcul des plongements contextuels...",
        "chatml.chart.contextual_embeddings": (
            "Un échantillon de vrais messages, projeté par sens contextuel"
        ),
        "chatml.no_word_embeddings": (
            "Pas assez de mots de contenu distincts dans l'échantillon pour les cartographier."
        ),
        "chatml.streamers_heading": "Segments comportementaux des streamers",
        "chatml.streamers_caption": (
            "Un vrai clustering non supervisé (K-Means) sur la forme de performance "
            "de chaque streamer — dons récoltés, taille d'audience, heures en direct, "
            "temps de disponibilité — regroupant les streamers selon leur événement, "
            "pas par catégorie ou équipe (il n'y a pas de dimension équipe dans ces "
            "données)."
        ),
        "chatml.streamers_n_clusters": "Nombre de segments comportementaux",
        "chatml.no_streamers_ml": (
            "Pas assez de streamers dans la plage sélectionnée pour former des "
            "segments comportementaux pour le moment."
        ),
        "chatml.column.streamers": "Streamers",
        "chatml.column.avg_amount": "Dons moy. (€)",
        "chatml.column.avg_avg_viewers": "Viewers moy.",
        "chatml.column.avg_hours_live": "Heures en direct moy.",
        "chatml.column.avg_uptime_pct": "Disponibilité moy. %",
        "chatml.column.streamer": "Streamer",
        "chatml.column.amount": "Dons (€)",
        "chatml.column.avg_viewers_short": "Viewers moy.",
        "chatml.streamers_examples_heading": "Voir des exemples de streamers par cluster",
        "chatml.explain.streamers": (
            "Chaque caractéristique est transformée en logarithme avant le "
            "clustering, même raisonnement que les segments de chatteurs ci-dessous "
            "— les vrais chiffres de dons/audience sont très asymétriques (confirmé "
            "sur des données réelles : les dons totaux vont de 0 € à plus de 2 M€ "
            "contre une médiane de 3,3 k€), et sans cette transformation une poignée "
            "de méga-collecteurs domineraient la formation des clusters au lieu de "
            "la forme du gros du plateau."
        ),
        "chatml.chatters_heading": "Segments comportementaux des chatteurs",
        "chatml.chatters_caption": (
            "Un vrai clustering non supervisé (K-Means) sur la forme d'activité de "
            "chaque chatteur — combien de chaînes il visite, combien il poste, combien "
            "de temps il reste — plus riche qu'une étiquette fixe "
            "« sédentaire / nomade » puisque les segments sont découverts à partir des "
            "données elles-mêmes, pas définis à l'avance. Les comptes probablement "
            "bots sont exclus au préalable."
        ),
        "chatml.chatters_n_clusters": "Nombre de segments comportementaux",
        "chatml.no_chatters": (
            "Pas assez de chatteurs dans la plage sélectionnée pour former des "
            "segments comportementaux pour le moment."
        ),
        "chatml.column.chatters": "Chatteurs",
        "chatml.column.chatter": "Chatteur",
        "chatml.column.avg_channels": "Chaînes moy.",
        "chatml.column.avg_messages": "Messages moy.",
        "chatml.column.avg_lifespan_hours": "Durée de vie moy. (h)",
        "chatml.column.avg_messages_per_channel": "Messages moy. / chaîne",
        "chatml.chatters_examples_heading": "Voir des exemples de chatteurs par cluster",
        "chatml.explain.chatters": (
            "Chaque caractéristique est transformée en logarithme avant le "
            "clustering — l'activité réelle des chatteurs est très asymétrique "
            "(une poignée de comptes postent des milliers de fois plus que la "
            "médiane), et sans cette transformation quelques comptes extrêmes "
            "domineraient la formation des clusters au lieu de la forme du gros de la "
            "population. Comparez les moyennes propres à un cluster à celles des "
            "autres pour voir ce qui le définit — un nombre moyen élevé de messages "
            "par chaîne avec peu de chaînes visitées se lit comme « superfan "
            "fidèle » ; beaucoup de chaînes avec peu de messages au total se lit "
            "comme « spectateur qui zappe entre les chaînes »."
        ),
        "chatml.outliers_heading": "Détection d'anomalies",
        "chatml.outliers_caption": (
            "Une vraie détection d'anomalies non supervisée (Isolation Forest) — "
            "signale les streamers, chatteurs, ou heures d'ambiance de chat dont les "
            "chiffres ne ressemblent au cas typique dans *aucune* des deux "
            "directions. Confirmé sur des données réelles : ceci fait ressortir à la "
            "fois les plus gros collecteurs de fonds de l'événement et ses entrées "
            "quasi inactives comme « statistiquement inhabituels » à la fois — une "
            "anomalie n'est pas automatiquement un problème, juste inhabituelle."
        ),
        "chatml.outliers_target_label": "Chercher des anomalies parmi",
        "chatml.outliers_target_streamers": "Streamers",
        "chatml.outliers_target_chatters": "Chatteurs",
        "chatml.outliers_target_hours": "Heures d'ambiance du chat",
        "chatml.outliers_contamination": "Fraction d'anomalies attendue",
        "chatml.no_outliers": (
            "Pas assez de lignes dans la plage sélectionnée pour détecter des "
            "anomalies pour le moment."
        ),
        "chatml.column.uptime_pct": "Disponibilité %",
        "chatml.column.anomaly_score": "Score d'anomalie",
        "chatml.column.hour": "Heure",
        "chatml.column.avg_hype": "Score de hype moy.",
        "chatml.column.avg_sentiment": "Score de sentiment moy.",
        "chatml.explain.outliers": (
            "« Fraction d'anomalies attendue » est le seul réglage d'Isolation "
            "Forest — augmentez-la pour voir plus de lignes signalées (et moins "
            "extrêmes), baissez-la pour ne voir que les quelques cas les plus "
            "extrêmes. Le « score d'anomalie » est la fonction de décision propre au "
            "modèle : plus négatif signifie plus anormal, donc les lignes les plus "
            "inhabituelles sont triées en premier. Les caractéristiques des "
            "streamers/chatteurs sont d'abord transformées en logarithme pour les "
            "mêmes raisons d'asymétrie que leurs sections de clustering ci-dessus ; "
            "les heures d'ambiance du chat ne le sont pas, le sentiment pouvant être "
            "négatif."
        ),
        "chatml.classify_heading": "Vrai modèle vs liste de mots : sentiment & toxicité",
        "chatml.classify_caption": (
            "Exécute de vrais modèles transformer pré-entraînés (pas des listes de "
            "mots) sur un petit échantillon de messages — certains déjà signalés "
            "comme hostiles par la liste de mots d'Intelligence du chat, d'autres au "
            "hasard — et compare leur verdict à celui de la liste de mots. Charge "
            "environ 1 à 2 Go de poids de modèle la première fois (mis en cache "
            "ensuite) ; cliquez pour lancer. Affiche la vraie chaîne et le vrai "
            "chatteur — mais ni le modèle ni la liste de mots n'est un "
            "classificateur certifié, donc lisez un signalement "
            "\"toxique\"/\"hostile\" comme une piste à vérifier en contexte, pas "
            "comme un verdict."
        ),
        "chatml.classify_button": "Lancer la classification ML",
        "chatml.classify_spinner": (
            "Exécution des modèles de sentiment et de toxicité (peut télécharger "
            "environ 1 à 2 Go la première fois)..."
        ),
        "chatml.no_classify": "Aucun message disponible à classifier dans la plage sélectionnée.",
        "chatml.classify_agreement": (
            "Le modèle ML de toxicité et la liste de mots sont d'accord sur {pct} % "
            "de cet échantillon. Leurs désaccords se situent généralement là où le "
            "contexte compte — voir le tableau ci-dessous."
        ),
        "chatml.column.channel_short": "Chaîne",
        "chatml.column.message": "Message",
        "chatml.column.lexicon_verdict": "La liste de mots dit hostile",
        "chatml.column.ml_sentiment": "Sentiment ML",
        "chatml.column.ml_toxicity": "Toxicité ML",
        "chatml.explain.classify": (
            "Modèle de sentiment : cardiffnlp/twitter-xlm-roberta-base-sentiment "
            "(multilingue, entraîné sur du texte de réseaux sociaux). Modèle de "
            "toxicité : textdetox/xlmr-large-toxicity-classifier — choisi après des "
            "tests sur du vrai chat : une alternative plus petite avait étiqueté avec "
            "confiance \"gg les gars, quel beau run\" (un message amical) comme "
            "toxique à 99 % et avait totalement raté une vraie insulte. Un modèle "
            "peut lire un contexte que la liste de mots ne peut pas — par exemple "
            "reconnaître \"ta gueule\" entre amis comme surtout joueur plutôt "
            "qu'hostile — ce qui est exactement pourquoi comparer les deux vaut le "
            "coup plutôt que de faire confiance à un seul."
        ),
        "chatml.classify_hint": (
            "Cliquez sur « Lancer la classification ML » ci-dessus pour charger les "
            "modèles et voir une comparaison — non exécuté automatiquement, car cela "
            "peut télécharger environ 1 à 2 Go la première fois."
        ),
        "chatml.column.pca1": "Composante principale 1",
        "chatml.column.pca2": "Composante principale 2",
        "chatml.chart.streamers_pca": "Segments de streamers, projetés en 2D (ACP)",
        "chatml.streamers_pca_caption": (
            "Chaque point est un streamer, coloré selon son cluster comportemental "
            "ci-dessus — le même espace à 7 variables sur lequel le clustering a "
            "été ajusté, projeté sur les 2 directions de plus grande variation pour "
            "que les segments soient réellement visibles, pas seulement tabulés. La "
            "distance sur ce graphique reflète la similarité de forme de "
            "performance entre deux streamers, pas leurs gains bruts. Survolez un "
            "point pour voir le nom du streamer et sa chaîne Twitch."
        ),
        "chatml.explain.streamers_pca": (
            "Trois étapes transforment les 7 variables brutes (`amount_eur`, "
            "`hours_live`, `avg_viewers`, `peak_viewers`, `unique_chatters`, "
            "`total_messages`, `uptime_pct`) en les 2 axes tracés ci-dessus — les "
            "mêmes étapes sur lesquelles `cluster_streamers` lui-même s'ajuste, "
            "donc cette vue correspond exactement aux clusters plutôt que d'être "
            "une projection choisie séparément :\n\n"
            "1. **Transformation logarithmique** de chaque variable pour atténuer "
            "son asymétrie à droite (`amount_eur` seul va de presque zéro à plus "
            "de 2 M€) : $x' = \\log(1+x)$.\n"
            "2. **Standardisation** pour qu'aucune variable ne domine par sa seule "
            "échelle brute : $z = \\dfrac{x' - \\mu}{\\sigma}$, avec la moyenne "
            "$\\mu$ et l'écart-type $\\sigma$ calculés par variable sur tous les "
            "streamers.\n"
            "3. **Projection** du vecteur standardisé à 7 dimensions $z$ de chaque "
            "streamer sur les 2 premières composantes principales $w_1, w_2$ — "
            "les 2 directions de l'espace à 7 dimensions (trouvées par "
            "décomposition en valeurs propres de la matrice de covariance de $z$) "
            "qui captent le plus de variance : $\\mathrm{PC}_i = z \\cdot w_i$.\n\n"
            "Les deux axes ne correspondent à aucune variable d'origine unique — "
            "chacun est un mélange pondéré des sept — donc lisez ce graphique pour "
            "la position *relative* et le regroupement, pas comme des valeurs "
            "littérales de dons ou de viewers."
        ),
        "chatml.chart.chatters_pca": "Segments de chatteurs, projetés en 2D (ACP)",
        "chatml.chatters_pca_caption": (
            "Même principe que le graphique ACP des streamers ci-dessus, sur "
            "l'espace des variables comportementales des chatteurs — chaque point "
            "est un chatteur, coloré selon son cluster. Survolez un point pour "
            "voir le nom du chatteur."
        ),
        "chatml.explain.chatters_pca": (
            "Même pipeline transformation log → standardisation → projection que "
            "le graphique ACP des streamers ci-dessus (voir son « Comment lire ce "
            "graphique » pour les formules), appliqué cette fois aux 6 variables "
            "comportementales des chatteurs (`distinct_channel_count`, "
            "`total_message_count`, `lifespan_hours`, "
            "`gap_coefficient_of_variation`, `avg_messages_per_channel`, "
            "`top_channel_share`) sur lesquelles `cluster_chatters` lui-même "
            "s'ajuste."
        ),
        "chatml.forecast_heading": "Prévision des dons à partir d'un instantané en cours d'événement",
        "chatml.forecast_caption": (
            "Une régression Random Forest entraînée à prédire le total final de "
            "dons de chaque streamer à partir d'un instantané de ses propres dons "
            "cumulés, viewers et activité de chat à une date antérieure — une "
            "véritable prévision d'un futur inconnu à partir d'un passé connu, pas "
            "une prédiction d'un nombre à partir de lui-même. Déplacez le curseur "
            "pour voir comment la précision évolue selon la précocité de "
            "l'instantané."
        ),
        "chatml.no_forecast": (
            "Pas assez de streamers dans la plage/le filtre sélectionné pour "
            "ajuster et évaluer un modèle de prévision."
        ),
        "chatml.forecast_cutoff": "Instant de l'instantané (fraction de la plage de dates sélectionnée)",
        "chatml.forecast_cutoff_caption": "Instantané pris à la date : {cutoff}",
        "chatml.forecast_r2": "R² (jeu de test)",
        "chatml.forecast_mae": "MAE (jeu de test)",
        "chatml.forecast_n_test": "Streamers réservés pour le test",
        "chatml.forecast_perfect_line": "Prédiction parfaite",
        "chatml.forecast_scatter_name": "Streamer",
        "chatml.chart.forecast_scatter": "Dons finaux prédits vs réels (jeu de test)",
        "chatml.forecast_axis_actual": "Dons finaux réels (€)",
        "chatml.forecast_axis_predicted": "Dons finaux prédits (€)",
        "chatml.chart.forecast_importance": "Sur quoi le modèle s'appuie le plus",
        "chatml.forecast_feature_amount": "Dons jusqu'ici",
        "chatml.forecast_feature_avg_viewers": "Viewers moy. jusqu'ici",
        "chatml.forecast_feature_peak_viewers": "Pic de viewers jusqu'ici",
        "chatml.forecast_feature_messages": "Messages de chat jusqu'ici",
        "chatml.explain.forecast": (
            "**Pourquoi ce n'est pas circulaire.** Prédire le total final d'un "
            "streamer à partir de ses propres statistiques *finales* (ex. viewers "
            "finaux) serait quasi tautologique — un nombre corrèle évidemment avec "
            "lui-même. Ici, chaque variable est prise strictement *avant* "
            "l'instant choisi, et seul ce qui se passe *après* est prédit — la "
            "même contrainte passé-seulement-prédit-le-futur que toute véritable "
            "prévision impose.\n\n"
            "**Pourquoi transformé en log.** Dons, viewers et nombres de messages "
            "sont tous fortement asymétriques (quelques méga-collecteurs, une "
            "longue traîne de petits) — ajuster sur $x' = \\log(1+x)$ empêche le "
            "modèle d'être dominé par le plus gros streamer à lui seul, puis les "
            "prédictions sont reconverties en euros ($x = e^{x'} - 1$) avant "
            "l'évaluation, donc le R²/MAE ci-dessus sont dans les mêmes unités "
            "que le graphique.\n\n"
            "**Comment lire les métriques**, pour $n$ streamers de test avec "
            "totaux finaux réels $y_i$ et prédits $\\hat y_i$ (moyenne réelle "
            "$\\bar y$) :\n"
            "- $R^2 = 1 - \\dfrac{\\sum_i (y_i - \\hat y_i)^2}"
            "{\\sum_i (y_i - \\bar y)^2}$ — proche de 1,0 signifie que "
            "l'instantané explique presque toute la variation des totaux finaux ; "
            "0 signifie qu'il n'explique pas mieux que deviner toujours la "
            "moyenne.\n"
            "- $\\mathrm{MAE} = \\dfrac{1}{n}\\sum_i |y_i - \\hat y_i|$ — l'erreur "
            "moyenne de prédiction, en euros.\n\n"
            "Les deux sont calculées uniquement sur le jeu de test de 25 % mis de "
            "côté — des streamers que le modèle n'a jamais vus pendant "
            "l'entraînement — une estimation honnête de l'erreur de prévision, "
            "pas gonflée par un test sur les données d'entraînement elles-mêmes."
        ),
    },
}
