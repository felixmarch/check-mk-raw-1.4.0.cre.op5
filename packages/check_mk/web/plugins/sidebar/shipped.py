#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import config
import views, time, dashboard
import pagetypes, table
import sites

import livestatus
import notifications
from valuespec import *
from lib import *
import cmk.paths
import cmk.store as store

#   .--About---------------------------------------------------------------.
#   |                       _    _                 _                       |
#   |                      / \  | |__   ___  _   _| |_                     |
#   |                     / _ \ | '_ \ / _ \| | | | __|                    |
#   |                    / ___ \| |_) | (_) | |_| | |_                     |
#   |                   /_/   \_\_.__/ \___/ \__,_|\__|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_about():
    html.write(_("Version: ") + cmk.__version__)
    html.open_ul()
    bulletlink(_("Homepage"),        "https://mathias-kettner.com/check_mk.html")
    bulletlink(_("Documentation"),   "https://mathias-kettner.com/checkmk.html")
    bulletlink(_("Download"),        "https://mathias-kettner.com/check_mk_download.html")
    bulletlink("Mathias Kettner",    "https://mathias-kettner.com")
    html.close_ul()

sidebar_snapins["about"] = {
    "title" : _("About Check_MK"),
    "description" : _("Version information and Links to Documentation, "
                      "Homepage and Download of Check_MK"),
    "render" : render_about,
    "allowed" : [ "admin", "user", "guest" ],
}

#.
#   .--Views---------------------------------------------------------------.
#   |                    __     ___                                        |
#   |                    \ \   / (_) _____      _____                      |
#   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
#   |                      \ V / | |  __/\ V  V /\__ \                     |
#   |                       \_/  |_|\___| \_/\_/ |___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def visuals_by_topic(permitted_visuals, default_order=None):
    if default_order is None:
        default_order = [
            _("Overview"),
            _("Hosts"),
            _("Host Groups"),
            _("Services"),
            _("Service Groups"),
            _("Metrics"),
            _("Business Intelligence"),
            _("Problems"),
        ]

    s = [ (_u(visual.get("topic") or _("Other")), _u(visual.get("title")), name, 'painters' in visual)
          for name, visual
          in permitted_visuals
          if not visual["hidden"] and not visual.get("mobile")]

    s.sort()

    result = []
    for topic in default_order:
        result.append((topic, s))

    rest = list(set([ t for (t, _t, _v, _i) in s if t not in default_order ]))
    rest.sort()
    for topic in rest:
        if topic:
            result.append((topic, s))

    return result

def render_views():
    views.load_views()
    dashboard.load_dashboards()

    def render_topic(topic, entries):
        first = True
        for t, title, name, is_view in entries:
            if is_view and config.visible_views and name not in config.visible_views:
                continue
            if is_view and config.hidden_views and name in config.hidden_views:
                continue
            if t == topic:
                if first:
                    html.begin_foldable_container("views", topic, False, topic, indent=True)
                    first = False
                if is_view:
                    bulletlink(title, "view.py?view_name=%s" % name, onclick = "return wato_views_clicked(this)")
                elif "?name=" in name:
                    bulletlink(title, name)
                else:
                    bulletlink(title, 'dashboard.py?name=%s' % name, onclick = "return wato_views_clicked(this)")

        # TODO: One day pagestypes should handle the complete snapin.
        # for page_type in pagetypes.all_page_types().values():
        #     if issubclass(page_type, pagetypes.PageRenderer):
        #         for t, title, url in page_type.sidebar_links():
        #             if t == topic:
        #                 bulletlink(title, url)

        if not first: # at least one item rendered
            html.end_foldable_container()

    # TODO: One bright day drop this whole visuals stuff and only use page_types
    page_type_topics = {}
    for page_type in pagetypes.all_page_types().values():
        if issubclass(page_type, pagetypes.PageRenderer):
            for t, title, url in page_type.sidebar_links():
                page_type_topics.setdefault(t, []).append((t, title, url, False))

    visuals_topics_with_entries = visuals_by_topic(views.permitted_views().items() + dashboard.permitted_dashboards().items())
    all_topics_with_entries = []
    for topic, entries in visuals_topics_with_entries:
        if topic in page_type_topics:
            entries = entries + page_type_topics[topic]
            del page_type_topics[topic]
        all_topics_with_entries.append((topic, entries))

    all_topics_with_entries += sorted(page_type_topics.items())

    for topic, entries in all_topics_with_entries:
        render_topic(topic, entries)


    links = []
    if config.user.may("general.edit_views"):
        if config.debug:
            links.append((_("Export"), "export_views.py"))
        links.append((_("Edit"), "edit_views.py"))
        footnotelinks(links)

sidebar_snapins["views"] = {
    "title" : _("Views"),
    "description" : _("Links to global views and dashboards"),
    "render" : render_views,
    "allowed" : [ "user", "admin", "guest" ],
}

#.
#   .--Dashboards----------------------------------------------------------.
#   |        ____            _     _                         _             |
#   |       |  _ \  __ _ ___| |__ | |__   ___   __ _ _ __ __| |___         |
#   |       | | | |/ _` / __| '_ \| '_ \ / _ \ / _` | '__/ _` / __|        |
#   |       | |_| | (_| \__ \ | | | |_) | (_) | (_| | | | (_| \__ \        |
#   |       |____/ \__,_|___/_| |_|_.__/ \___/ \__,_|_|  \__,_|___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_dashboards():
    dashboard.load_dashboards()

    def render_topic(topic, s, foldable = True):
        first = True
        for t, title, name, is_view in s:
            if t == topic:
                if first:
                    if foldable:
                        html.begin_foldable_container("dashboards", topic, False, topic, indent=True)
                    else:
                        html.open_ul()
                    first = False
                bulletlink(title, 'dashboard.py?name=%s' % name, onclick = "return wato_views_clicked(this)")

        if not first: # at least one item rendered
            if foldable:
                html.end_foldable_container()
            else:
                html.open_ul()

    by_topic = visuals_by_topic(dashboard.permitted_dashboards().items(), default_order = [ _('Overview') ])
    topics = [ topic for topic, entry in by_topic ]

    if len(topics) < 2:
        render_topic(by_topic[0][0], by_topic[0][1], foldable = False)

    else:
        for topic, s in by_topic:
            render_topic(topic, s)

    links = []
    if config.user.may("general.edit_dashboards"):
        if config.debug:
            links.append((_("Export"), "export_dashboards.py"))
        links.append((_("Edit"), "edit_dashboards.py"))
        footnotelinks(links)

sidebar_snapins["dashboards"] = {
    "title"       : _("Dashboards"),
    "description" : _("Links to all dashboards"),
    "render"      : render_dashboards,
    "allowed"     : [ "user", "admin", "guest" ],
}

#.
#   .--Groups--------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   '----------------------------------------------------------------------'

def render_groups(what):
    data = sites.live().query("GET %sgroups\nColumns: name alias\n" % what)
    name_to_alias = dict(data)
    groups = [(name_to_alias[name].lower(), name_to_alias[name], name) for name in name_to_alias.keys()]
    groups.sort() # sort by Alias in lowercase
    html.open_ul()
    for alias_lower, alias, name in groups:
        url = "view.py?view_name=%sgroup&%sgroup=%s" % (what, what, html.urlencode(name))
        bulletlink(alias or name, url)
    html.close_ul()

sidebar_snapins["hostgroups"] = {
    "title" : _("Host Groups"),
    "description" : _("Directs links to all host groups"),
    "render" : lambda: render_groups("host"),
    "restart":     True,
    "allowed" : [ "user", "admin", "guest" ]
}
sidebar_snapins["servicegroups"] = {
    "title" : _("Service Groups"),
    "description" : _("Direct links to all service groups"),
    "render" : lambda: render_groups("service"),
    "restart":     True,
    "allowed" : [ "user", "admin", "guest" ]
}

#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_hosts(mode):
    sites.live().set_prepend_site(True)
    query = "GET hosts\nColumns: name state worst_service_state\nLimit: 100\n"
    view = "host"

    if mode == "summary":
        query += "Filter: custom_variable_names >= _REALNAME\n"
    else:
        query += "Filter: custom_variable_names < _REALNAME\n"

    if mode == "problems":
        view = "problemsofhost"
        # Exclude hosts and services in downtime
        svc_query = "GET services\nColumns: host_name\n"\
                    "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\n"\
                    "Filter: host_scheduled_downtime_depth = 0\nAnd: 3"
        problem_hosts = set(map(lambda x: x[1], sites.live().query(svc_query)))

        query += "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\nAnd: 2\n"
        for host in problem_hosts:
            query += "Filter: name = %s\n" % host
        query += "Or: %d\n" % (len(problem_hosts) + 1)

    hosts = sites.live().query(query)
    sites.live().set_prepend_site(False)
    hosts.sort()

    longestname = 0
    for site, host, state, worstsvc in hosts:
        longestname = max(longestname, len(host))
    if longestname > 15:
        num_columns = 1
    else:
        num_columns = 2

    views.load_views()
    target = views.get_context_link(config.user.id, view)
    html.open_table(class_="allhosts")
    col = 1
    for site, host, state, worstsvc in hosts:
        if col == 1:
            html.open_tr()
        html.open_td()

        if state > 0 or worstsvc == 2:
            statecolor = 2
        elif worstsvc == 1:
            statecolor = 1
        elif worstsvc == 3:
            statecolor = 3
        else:
            statecolor = 0
        html.open_div(class_=["statebullet", "state%d" % statecolor])
        html.write("&nbsp;")
        html.close_div()
        link(host, target + "&host=%s&site=%s" % (html.urlencode(host), html.urlencode(site)))
        html.close_td()
        if col == num_columns:
            html.close_tr()
            col = 1
        else:
            col += 1

    if col < num_columns:
        html.close_tr()
    html.close_table()

snapin_allhosts_styles = """
  .snapin table.allhosts { width: 100%; }
  .snapin table.allhosts td { width: 50%; padding: 0px 0px; }
"""

sidebar_snapins["hosts"] = {
    "title" : _("All Hosts"),
    "description" : _("A summary state of each host with a link to the view "
                      "showing its services"),
    "render" : lambda: render_hosts("hosts"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : True,
    "styles" : snapin_allhosts_styles,
}

sidebar_snapins["summary_hosts"] = {
    "title" : _("Summary Hosts"),
    "description" : _("A summary state of all summary hosts (summary hosts hold "
                      "aggregated service states and are a feature of Check_MK)"),
    "render" : lambda: render_hosts("summary"),
    "allowed" : [],
    "refresh" : True,
    "styles" : snapin_allhosts_styles,
}

sidebar_snapins["problem_hosts"] = {
    "title" : _("Problem Hosts"),
    "description" : _("A summary state of all hosts that have a problem, with "
                      "links to problems of those hosts"),
    "render" : lambda: render_hosts("problems"),
    "allowed" : [ "user", "admin", "guest" ],
    "refresh" : True,
    "styles" : snapin_allhosts_styles,
}

#.
#   .--Host Matrix---------------------------------------------------------.
#   |         _   _           _     __  __       _        _                |
#   |        | | | | ___  ___| |_  |  \/  | __ _| |_ _ __(_)_  __          |
#   |        | |_| |/ _ \/ __| __| | |\/| |/ _` | __| '__| \ \/ /          |
#   |        |  _  | (_) \__ \ |_  | |  | | (_| | |_| |  | |>  <           |
#   |        |_| |_|\___/|___/\__| |_|  |_|\__,_|\__|_|  |_/_/\_\          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_hostmatrix():
    sites.live().set_prepend_site(True)
    query = "GET hosts\n" \
            "Columns: name state has_been_checked worst_service_state scheduled_downtime_depth\n" \
            "Filter: custom_variable_names < _REALNAME\n" \
            "Limit: 901\n"
    hosts = sites.live().query(query)
    sites.live().set_prepend_site(False)
    hosts.sort()
    if len(hosts) > 900:
        html.write_text(_("Sorry, I will not display more than 900 hosts."))
        return

    # Choose smallest square number large enough
    # to show all hosts
    num_hosts = len(hosts)
    n = 1
    while n*n < num_hosts:
        n += 1

    rows = num_hosts / n
    lastcols = num_hosts % n
    if lastcols > 0:
        rows += 1

    # Calculate cell size (Automatic sizing with 100% does not work here)
    # - Get cell spacing: 1px between each cell
    # - Substract the cell spacing for each column from the total width
    # - Then divide the total width through the number of columns
    # - Then get the full-digit width of the cell and summarize the rest
    #   to be substracted from the cell width
    # This is not a 100% solution but way better than having no links
    cell_spacing = 1
    cell_size = ((snapin_width - cell_spacing * (n+1)) / n)
    cell_size, cell_size_rest = divmod(cell_size, 1)
    style = 'width:%spx' % (snapin_width - n * cell_size_rest)

    html.open_table(class_=["content_center", "hostmatrix"], cellspacing=0, style=["border-collapse:collapse;", style])
    col = 1
    row = 1
    for site, host, state, has_been_checked, worstsvc, downtimedepth in hosts:
        if col == 1:
            html.open_tr()
        if downtimedepth > 0:
            s = "d"
        elif not has_been_checked:
            s = "p"
        elif worstsvc == 2 or state == 1:
            s = 2
        elif worstsvc == 3 or state == 2:
            s = 3
        elif worstsvc == 1:
            s = 1
        else:
            s = 0
        url = "view.py?view_name=host&site=%s&host=%s" % (html.urlencode(site), html.urlencode(host))
        html.open_td(class_=["state", "state%s" % s])
        html.a('', href=url, title=host, target="main", style=["width:%spx;" % cell_size, "height:%spx;" % cell_size])
        html.close_td()

        if col == n or (row == rows and n == lastcols):
            html.open_tr()
            col = 1
            row += 1
        else:
            col += 1
    html.close_table()


sidebar_snapins["hostmatrix"] = {
    "title"       : _("Host Matrix"),
    "description" : _("A matrix showing a colored square for each host"),
    "render"      : render_hostmatrix,
    "allowed"     : [ "user", "admin", "guest" ],
    "refresh"     : True,
    "styles"      : """
table.hostmatrix { border-spacing: 0;  }
table.hostmatrix tr { padding: 0; border-spacing: 0; }
table.hostmatrix a { display: block; width: 100%; height: 100%; line-height: 100%; }
table.hostmatrix td { border: 1px solid #123a4a; padding: 0; border-spacing: 0; }
    """

}

#.
#   .--Site Status---------------------------------------------------------.
#   |           ____  _ _         ____  _        _                         |
#   |          / ___|(_) |_ ___  / ___|| |_ __ _| |_ _   _ ___             |
#   |          \___ \| | __/ _ \ \___ \| __/ _` | __| | | / __|            |
#   |           ___) | | ||  __/  ___) | || (_| | |_| |_| \__ \            |
#   |          |____/|_|\__\___| |____/ \__\__,_|\__|\__,_|___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_sitestatus():
    if config.is_multisite():
        html.open_table(cellspacing=0, class_="sitestate")

        sites.update_site_states_from_dead_sites()

        for sitename, sitealias in config.sorted_sites():
            site = config.site(sitename)

            state = sites.state(sitename, {})

            if state.get("state") == None:
                state = "missing"
                text = _("Missing site")
                title = _("Site %s does not exist") % sitename

            else:
                if state["state"] == "disabled":
                    switch = "on"
                    text = site["alias"]
                    title = _("Site %s is switched off") % site["alias"]
                else:
                    switch = "off"
                    text = render_link(site["alias"], "view.py?view_name=sitehosts&site=%s" % sitename)
                    ex = state.get("exception")
                    shs = state.get("status_host_state")

                    if ex:
                        title = ex
                    else:
                        title = "Site %s is online" % site["alias"]

            html.open_tr()
            html.open_td(class_="left")
            html.write(text)
            html.close_td()
            html.open_td(class_="state")
            html.status_label_button(content=state["state"], status=state["state"],
                help=_("%s this site") % (state["state"] == "disabled" and _("enable") or _("disable")),
                onclick="switch_site('_site_switch=%s:%s')" % (sitename, switch))
            html.close_tr()
        html.close_table()


sidebar_snapins["sitestatus"] = {
  "title" : _("Site Status"),
  "description" : _("Connection state of each site and button for enabling "
                    "and disabling the site connection"),
  "render" : render_sitestatus,
  "allowed" : [ "user", "admin" ],
  "refresh" : True,
  "styles" : """
table.sitestate {
    width: %dpx;
}

table.sitestate td {
    padding: 1px 0px;
    text-align: right;
}

table.sitestate td.left {
    text-align: left;
}

div.snapin table.sitestate td img.iconbutton {
    width: 60px;
    height: 16px;
}

table.sitestate td.left a {
    text-align: left;
    font-weight: normal;
}

table.sitestate td.state {
    width: 60px;
    font-size: 7pt;
}

""" % snapin_width
}

#.
#   .--Tactical Overv.-----------------------------------------------------.
#   |    _____          _   _           _    ___                           |
#   |   |_   _|_ _  ___| |_(_) ___ __ _| |  / _ \__   _____ _ ____   __    |
#   |     | |/ _` |/ __| __| |/ __/ _` | | | | | \ \ / / _ \ '__\ \ / /    |
#   |     | | (_| | (__| |_| | (_| (_| | | | |_| |\ V /  __/ |   \ V /     |
#   |     |_|\__,_|\___|\__|_|\___\__,_|_|  \___/  \_/ \___|_|    \_(_)    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def get_tactical_overview_data(extra_filter_headers):
    configured_staleness_threshold = config.staleness_threshold

    host_query = \
        "GET hosts\n" \
        "Stats: state >= 0\n" \
        "Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "StatsAnd: 2\n" \
        "Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: acknowledged = 0\n" \
        "StatsAnd: 3\n" \
        "Stats: host_staleness >= %s\n" % configured_staleness_threshold + \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "StatsAnd: 2\n" \
        "Filter: custom_variable_names < _REALNAME\n" + \
        extra_filter_headers

    service_query = \
        "GET services\n" \
        "Stats: state >= 0\n" \
        "Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: host_state = 0\n" \
        "StatsAnd: 4\n" \
        "Stats: state > 0\n" \
        "Stats: scheduled_downtime_depth = 0\n" \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: acknowledged = 0\n" \
        "Stats: host_state = 0\n" \
        "StatsAnd: 5\n" \
        "Stats: service_staleness >= %s\n" % configured_staleness_threshold + \
        "Stats: host_scheduled_downtime_depth = 0\n" \
        "Stats: service_scheduled_downtime_depth = 0\n" \
        "StatsAnd: 3\n" \
        "Filter: host_custom_variable_names < _REALNAME\n" + \
        extra_filter_headers

    # In case the user is not allowed to see unrelated events
    ec_filters = ""
    if not config.user.may("mkeventd.seeall") and not config.user.may("mkeventd.seeunrelated"):
        ec_filters = "Filter: event_contact_groups != \n" \
                   + "Filter: host_name != \n" \
                   + "Or: 2\n"

    event_query = (
        # "Events" column
        "GET eventconsoleevents\n"
        "Stats: event_phase = open\n"
        "Stats: event_phase = ack\n"
        "StatsOr: 2\n"
        # "Problems" column
        "Stats: event_phase = open\n"
        "Stats: event_phase = ack\n"
        "StatsOr: 2\n"
        "Stats: event_state != 0\n"
        "StatsAnd: 2\n"
        # "Unhandled" column
        "Stats: event_phase = open\n"
        "Stats: event_state != 0\n"
        "StatsAnd: 2\n"
        + ec_filters
    )

    try:
        hstdata = sites.live().query_summed_stats(host_query)
        svcdata = sites.live().query_summed_stats(service_query)

        notdata = notifications.load_failed_notifications(
                        after=notifications.acknowledged_time(),
                        stat_only=True,
                        extra_headers=extra_filter_headers)

        try:
            sites.live().set_auth_domain("ec")
            event_data = sites.live().query_summed_stats(event_query)
        except livestatus.MKLivestatusNotFoundError:
            event_data = [0, 0, 0]
        finally:
            sites.live().set_auth_domain("read")

    except livestatus.MKLivestatusNotFoundError:
        return None, None, None, None

    return hstdata, svcdata, notdata, event_data


def render_tactical_overview(extra_filter_headers="", extra_url_variables=None):
    if extra_url_variables is None:
        extra_url_variables = []

    hstdata, svcdata, notdata, event_data = get_tactical_overview_data(extra_filter_headers)

    if hstdata is None or svcdata is None or notdata is None or event_data is None:
        html.center(_("No data from any site"))
        return

    td_class = 'col3'
    if hstdata[-1] or svcdata[-1]:
        td_class = 'col4'

    rows = [
        {
            "what"  : 'host',
            "title" : _("Hosts"),
            "data"  : hstdata,
            "views" : {
                "all"       : [
                    ("view_name", "allhosts"),
                ],
                "handled"   : [
                    ("view_name", 'hostproblems'),
                ],
                "unhandled" : [
                    ("view_name", "hostproblems"),
                    ("is_host_acknowledged", 0),
                ],
                "stale"     : [
                    ("view_name", 'stale_hosts'),
                ],
            },
        },
        {
            "what"  : "service",
            "title" : _("Services"),
            "data"  : svcdata,
            "views" : {
                "all"       : [
                    ("view_name", "allservices"),
                ],
                "handled"   : [
                    ("view_name", "svcproblems"),
                ],
                "unhandled" : [
                    ("view_name", "svcproblems"),
                    ("is_service_acknowledged", 0),
                ],
                "stale"     : [
                    ("view_name", "uncheckedsvc"),
                ],
            },
        },
        {
            "what"  : "event",
            "title" : _("Events"),
            "data"  : event_data,
            "views" : {
                "all"       : [
                    ("view_name", "ec_events"),
                ],
                "handled"   : [
                    ("view_name", "ec_events"),
		    ("event_state_1", "on",),
		    ("event_state_2", "on",),
		    ("event_state_3", "on",),

                ],
                "unhandled" : [
                    ("view_name", "ec_events"),
                    ("event_phase_open", "on"),
		    ("event_state_1", "on",),
                    ("event_state_2", "on",),
                    ("event_state_3", "on",),
                ],
                "stale"     : None,
            },
        },
    ]

    html.open_table(class_=["content_center", "tacticaloverview"], cellspacing=2, cellpadding=0, border=0)

    for row in rows:
        if row["what"] == "event":
            amount, problems, unhandled_problems = row["data"]
            stales = 0

            # no events open and disabled in local site: don't show events
            if amount == 0 and not config.mkeventd_enabled:
                continue
        else:
            amount, problems, unhandled_problems, stales = row["data"]

        html.open_tr()
        html.th(row["title"])
        html.th(_("Problems"))
        html.th(_("Unhandled"))
        if td_class == 'col4':
            html.th(_("Stale"))
        html.close_tr()

        html.open_tr()
        url = html.makeuri_contextless(row["views"]["all"] + extra_url_variables,filename="view.py")
        html.open_td(class_=["total", td_class])
        html.a(amount, href=url, target="main")
        html.close_td()

        for value, ty in [ (problems, "handled"), (unhandled_problems, "unhandled") ]:
            url = html.makeuri_contextless(row["views"][ty] + extra_url_variables, filename="view.py")
            html.open_td(class_=[td_class, "states prob" if value != 0 else None])
            link(str(value), url)
            html.close_td()

        if td_class == 'col4':
            if row["views"]["stale"]:
                url = html.makeuri_contextless(row["views"]["stale"] + extra_url_variables, filename="view.py")
                html.open_td(class_=[td_class, "states prob" if stales != 0 else None])
                link(str(stales), url)
                html.close_td()
            else:
                html.td('')

        html.close_tr()
    html.close_table()

    failed_notifications = notdata[0]
    if failed_notifications:
        html.open_div(class_="spacertop")
        html.open_div(class_="tacticalalert")

        confirm_url = html.makeuri_contextless(extra_url_variables,
                                               filename="clear_failed_notifications.py")
        html.icon_button(confirm_url, _("Confirm failed notifications"), "delete", target="main")

        view_url = html.makeuri_contextless(
            [("view_name", "failed_notifications")] + extra_url_variables, filename="view.py")

        html.a(_("%d failed notifications") % failed_notifications, target="main", href=view_url)
        html.close_div()
        html.close_div()


snapin_tactical_overview_styles = """
table.tacticaloverview {
   border-collapse: separate;
   width: %dpx;
   margin-top: -7px;
}
table.tacticaloverview th {
    font-size: 8pt;
    line-height: 7pt;
    text-align: left;
    color: #123a4a;
    font-weight: normal;
    padding: 0;
    padding-top: 2px;
    vertical-align: bottom;
}
table.tacticaloverview td {
    text-align: right;
    background-color: #6da1b8;
    padding: 0px;
    height: 14px;
}
table.tacticaloverview td.prob {
    box-shadow: 0px 0px 4px #ffd000;
}
table.tacticaloverview td.col3 {
    width:33%%;
}
table.tacticaloverview td.col4 {
    width:25%%;
}
table.tacticaloverview a { display: block; margin-right: 2px; }
div.tacticalalert {
    font-size: 9pt;
    line-height: 25px;
    height: 25px;
    text-align: center;
    background-color: #ff5500;
    box-shadow: 0px 0px 4px #ffd000;
}
div.spacertop {
    padding-top: 5px;
}
#snapin_tactical_overview img {
    width: 15px;
    height: auto;
    position: relative;
    top: -1px;
}

""" % snapin_width


sidebar_snapins["tactical_overview"] = {
    "title" : _("Tactical Overview"),
    "description" : _("The total number of hosts and service with and without problems"),
    "refresh" : True,
    "render" : render_tactical_overview,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : snapin_tactical_overview_styles,
}

#.
#   .--Performance---------------------------------------------------------.
#   |    ____            __                                                |
#   |   |  _ \ ___ _ __ / _| ___  _ __ _ __ ___   __ _ _ __   ___ ___      |
#   |   | |_) / _ \ '__| |_ / _ \| '__| '_ ` _ \ / _` | '_ \ / __/ _ \     |
#   |   |  __/  __/ |  |  _| (_) | |  | | | | | | (_| | | | | (_|  __/     |
#   |   |_|   \___|_|  |_|  \___/|_|  |_| |_| |_|\__,_|_| |_|\___\___|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_performance():
    only_sites = snapin_site_choice("performance",
                                    config.site_choices())

    def write_line(left, right):
        html.open_tr()
        html.td(left, class_="left")
        html.td(html.render_strong(right), class_="right")
        html.close_tr()

    html.open_table(class_=["content_center", "performance"])

    try:
        sites.live().set_only_sites(only_sites)
        data = sites.live().query(
            "GET status\nColumns: service_checks_rate host_checks_rate "
            "external_commands_rate connections_rate forks_rate "
            "log_messages_rate cached_log_messages\n")
    finally:
        sites.live().set_only_sites(None)

    for what, col, format in \
        [("Service checks",         0, "%.2f/s"),
         ("Host checks",            1, "%.2f/s"),
         ("External commands",      2, "%.2f/s"),
         ("Livestatus-conn.",       3, "%.2f/s"),
         ("Process creations",      4, "%.2f/s"),
         ("New log messages",       5, "%.2f/s"),
         ("Cached log messages",    6, "%d")]:
        write_line(what + ":", format % sum(row[col] for row in data))

    if only_sites is None and len(config.allsites()) == 1:
        try:
            data = sites.live().query("GET status\nColumns: external_command_buffer_slots "
                                   "external_command_buffer_max\n")
        finally:
            sites.live().set_only_sites(None)
        size = sum([row[0] for row in data])
        maxx = sum([row[1] for row in data])
        write_line(_('Com. buf. max/total'), "%d / %d" % (maxx, size))

    html.close_table()


sidebar_snapins["performance"] = {
    "title" : _("Server Performance"),
    "description" : _("Live monitor of the overall performance of all monitoring servers"),
    "refresh" : True,
    "render" : render_performance,
    "allowed" : [ "admin", ],
    "styles" : """
#snapin_performance select {
    margin-bottom: 2px;
    width: 100%%;
}
table.performance {
    width: %dpx;
    border-radius: 2px;
    background-color: rgba(0, 0, 0, 0.1);
    border-style: solid;
    border-color: rgba(0, 0, 0, 0.3) rgba(255, 255, 255, 0.3) rgba(255, 255, 255, 0.3) rgba(0, 0, 0, 0.3);
    border-width: 1.5px;
}
table.performance td {
    padding: 0px 2px;
    font-size: 8pt;
}
table.performance td.right {
    text-align: right;
    padding: 0px;
    padding-right: 1px;
    white-space: nowrap;
}

""" % (snapin_width - 2)
}

#.
#   .--Speedometer---------------------------------------------------------.
#   |    ____                      _                      _                |
#   |   / ___| _ __   ___  ___  __| | ___  _ __ ___   ___| |_ ___ _ __     |
#   |   \___ \| '_ \ / _ \/ _ \/ _` |/ _ \| '_ ` _ \ / _ \ __/ _ \ '__|    |
#   |    ___) | |_) |  __/  __/ (_| | (_) | | | | | |  __/ ||  __/ |       |
#   |   |____/| .__/ \___|\___|\__,_|\___/|_| |_| |_|\___|\__\___|_|       |
#   |         |_|                                                          |
#   '----------------------------------------------------------------------'

def render_speedometer():
    html.open_div(class_="speedometer")
    html.img("images/speedometer.png", id_="speedometerbg")
    html.canvas('', width=228, height=136, id_="speedometer")
    html.close_div()

    html.javascript("""
function show_speed(percentage) {
    var canvas = document.getElementById('speedometer');
    if (!canvas)
        return;

    var context = canvas.getContext('2d');
    if (!context)
        return;

    if (percentage > 100.0)
        percentage = 100.0;

    var orig_x = 116;
    var orig_y = 181;
    var angle_0   = 232.0;
    var angle_100 = 307.0;
    var angle = angle_0 + (angle_100 - angle_0) * percentage / 100.0;
    var angle_rad = angle / 360.0 * Math.PI * 2;
    var length = 120;
    var end_x = orig_x + (Math.cos(angle_rad) * length);
    var end_y = orig_y + (Math.sin(angle_rad) * length);

    context.clearRect(0, 0, 228, 136);
    context.beginPath();
    context.moveTo(orig_x, orig_y);
    context.lineTo(end_x, end_y);
    context.closePath();
    context.shadowOffsetX = 2;
    context.shadowOffsetY = 2;
    context.shadowBlur = 2;
    context.strokeStyle = "#000000";
    context.stroke();
    context = null;
}

function speedometer_show_speed(last_perc, program_start, scheduled_rate)
{
    try {
        text = get_url_sync("sidebar_ajax_speedometer.py" +
                            "?last_perc=" + last_perc +
                            "&scheduled_rate=" + scheduled_rate +
                            "&program_start=" + program_start);
        code = eval(text);
        scheduled_rate = code[0];
        program_start    = code[1];
        percentage       = code[2];
        last_perc        = code[3];
        title            = code[4];

        oDiv = document.getElementById('speedometer');

        // Terminate reschedule when the speedometer div does not exist anymore
        // (e.g. the snapin has been removed)
        if (!oDiv)
            return;

        oDiv.title = title
        oDiv = document.getElementById('speedometerbg');
        oDiv.title = title
        oDiv = null;

        move_needle(last_perc, percentage); // 50 * 100ms = 5s = refresh time
    } catch(ie) {
        // Ignore errors during re-rendering. Proceed with reschedule...
    }

    // large timeout for fetching new data via Livestatus
    setTimeout("speedometer_show_speed("
        + percentage       + ","
        + program_start    + ","
        + scheduled_rate + ");", 5000);
}

var needle_timeout = null;

function move_needle(from_perc, to_perc)
{
    new_perc = from_perc * 0.9 + to_perc * 0.1;
    show_speed(new_perc);
    if (needle_timeout != null)
        clearTimeout(needle_timeout);
    needle_timeout = setTimeout("move_needle(" + new_perc + "," +  to_perc + ");", 50);
}


speedometer_show_speed(0, 0, 0);

""")



sidebar_snapins["speedometer"] = {
    "title" : _("Service Speed-O-Meter"),
    "description" : _("A gadget that shows your current service check rate in relation to "
                      "the scheduled check rate. If the Speed-O-Meter shows a speed "
                      "of 100 percent, all service checks are being executed in exactly "
                      "the rate that is desired."),
    "render" : render_speedometer,
    "allowed" : [ "admin", ],
    "styles" : """
div.speedometer {
    position: relative;
    top: 0px;
    left: 0px;
    height: 223px;
}
img#speedometerbg {
    position: absolute;
    top: 0px;
    left: 0px;
}
canvas#speedometer {
    position: absolute;
    top: 0px;
    left: 0px;
}
"""}

#.
#   .--Server Time---------------------------------------------------------.
#   |       ____                             _____ _                       |
#   |      / ___|  ___ _ ____   _____ _ __  |_   _(_)_ __ ___   ___        |
#   |      \___ \ / _ \ '__\ \ / / _ \ '__|   | | | | '_ ` _ \ / _ \       |
#   |       ___) |  __/ |   \ V /  __/ |      | | | | | | | | |  __/       |
#   |      |____/ \___|_|    \_/ \___|_|      |_| |_|_| |_| |_|\___|       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_current_time():
    import time
    html.div(time.strftime("%H:%M"), class_="time")

sidebar_snapins["time"] = {
    "title" : _("Server Time"),
    "description" : _("A large clock showing the current time of the web server"),
    "refresh" : True,
    "render" : render_current_time,
    "allowed" : [ "user", "admin", "guest", ],
    "styles" : """
div.time {
   text-align: center;
   font-size: 18pt;
   font-weight: bold;
   /* The border needs to be substracted from the width */
   border: 1px solid #8cc;
   -moz-border-radius: 10px;
   background-color: #588;
   color: #aff;
   width: %dpx;
}
"""  % (snapin_width - 2)
}

#.
#   .--Nagios--------------------------------------------------------------.
#   |                    _   _             _                               |
#   |                   | \ | | __ _  __ _(_) ___  ___                     |
#   |                   |  \| |/ _` |/ _` | |/ _ \/ __|                    |
#   |                   | |\  | (_| | (_| | | (_) \__ \                    |
#   |                   |_| \_|\__,_|\__, |_|\___/|___/                    |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'

def render_nagios():
    html.open_ul()
    bulletlink("Home", "http://www.nagios.org")
    bulletlink("Documentation", "%snagios/docs/toc.html" % config.url_prefix())
    html.close_ul()
    for entry in [
        "General",
        ("tac.cgi", "Tactical Overview"),
        ("statusmap.cgi?host=all", "Map"),
        "Current Status",
        ("status.cgi?hostgroup=all&amp;style=hostdetail", "Hosts"),
        ("status.cgi?host=all", "Services"),
        ("status.cgi?hostgroup=all&amp;style=overview", "Host Groups"),
        ("status.cgi?hostgroup=all&amp;style=summary", "*Summary"),
        ("status.cgi?hostgroup=all&amp;style=grid", "*Grid"),
        ("status.cgi?servicegroup=all&amp;style=overview", "Service Groups"),
        ("status.cgi?servicegroup=all&amp;style=summary", "*Summary"),
        ("status.cgi?servicegroup=all&amp;style=grid", "*Grid"),
        ("status.cgi?host=all&amp;servicestatustypes=28", "Problems"),
        ("status.cgi?host=all&amp;type=detail&amp;hoststatustypes=3&amp;serviceprops=42&amp;servicestatustypes=28", "*Service (Unhandled)"),
        ("status.cgi?hostgroup=all&amp;style=hostdetail&amp;hoststatustypes=12&amp;hostprops=42", "*Hosts (Unhandled)"),
        ("outages.cgi", "Network Outages"),
        "Reports",
        ("avail.cgi", "Availability"),
        ("trends.cgi", "Trends"),
        ("history.cgi?host=all", "Alerts"),
        ("history.cgi?host=all", "*History"),
        ("summary.cgi", "*Summary"),
        ("histogram.cgi", "*Histogram"),
        ("notifications.cgi?contact=all", "Notifications"),
        ("showlog.cgi", "Event Log"),
        "System",
        ("extinfo.cgi?type=3", "Comments"),
        ("extinfo.cgi?type=6", "Downtime"),
        ("extinfo.cgi?type=0", "Process Info"),
        ("extinfo.cgi?type=4", "Performance Info"),
        ("extinfo.cgi?type=7", "Scheduling Queue"),
        ("config.cgi", "Configuration"),
        ]:
        if type(entry) == str:
            html.close_ul()
            heading(entry)
            html.open_ul()
        else:
            ref, text = entry
            if text[0] == "*":
                html.open_ul(class_="link")
                nagioscgilink(text[1:], ref)
                html.close_ul()
            else:
                nagioscgilink(text, ref)

sidebar_snapins["nagios_legacy"] = {
    "title" : _("Old Nagios GUI"),
    "description" : _("The classical sidebar of Nagios 3.2.0 with links to "
                      "your local Nagios instance (no multi site support)"),
    "render" : render_nagios,
    "allowed" : [ "user", "admin", "guest", ],
}


#.
#   .--Master Control------------------------------------------------------.
#   |  __  __           _               ____            _             _    |
#   | |  \/  | __ _ ___| |_ ___ _ __   / ___|___  _ __ | |_ _ __ ___ | |   |
#   | | |\/| |/ _` / __| __/ _ \ '__| | |   / _ \| '_ \| __| '__/ _ \| |   |
#   | | |  | | (_| \__ \ ||  __/ |    | |__| (_) | | | | |_| | | (_) | |   |
#   | |_|  |_|\__,_|___/\__\___|_|     \____\___/|_| |_|\__|_|  \___/|_|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_master_control():
    items = [
        ( "enable_notifications",     _("Notifications" )),
        ( "execute_service_checks",   _("Service checks" )),
        ( "execute_host_checks",      _("Host checks" )),
        ( "enable_flap_detection",    _("Flap Detection" )),
        ( "enable_event_handlers",    _("Event handlers" )),
        ( "process_performance_data", _("Performance data" )),
        ( "enable_event_handlers",    _("Alert handlers" )),
    ]

    sites.update_site_states_from_dead_sites()

    site_status_info = {}
    try:
        sites.live().set_prepend_site(True)
        for row in sites.live().query("GET status\nColumns: %s" %
                                        " ".join([ i[0] for i in items ])):
            site_id, values = row[0], row[1:]
            site_status_info[site_id] = values
    finally:
        sites.live().set_prepend_site(False)

    for site_id, site_alias in config.sorted_sites():
        if not config.is_single_local_site():
            html.begin_foldable_container("master_control", site_id, True, site_alias)

        site_state = sites.state(site_id)
        if site_state["state"] == "dead":
            html.show_error(site_state["exception"])

        else:
            is_cmc = site_state["program_version"].startswith("Check_MK ")

            try:
                site_info = site_status_info[site_id]
            except KeyError:
                site_info = None

            html.open_table(class_="master_control")
            for i, (colname, title) in enumerate(items):
                # Do not show event handlers on Check_MK Micro Core
                if is_cmc and title == _("Event handlers"):
                    continue
                elif not is_cmc and title == _("Alert handlers"):
                    continue

                colvalue = site_info[i]
                url = config.url_prefix() + ("check_mk/switch_master_state.py?site=%s&switch=%s&state=%d" % (site_id, colname, 1 - colvalue))
                onclick = "get_url('%s', updateContents, 'snapin_master_control')" % url

                html.open_tr()
                html.td(title, class_="left")
                html.open_td()
                html.toggle_switch(
                    enabled=colvalue,
                    help=_("Switch '%s' to '%s'") % (title, _("off") if colvalue else _("on")),
                    onclick=onclick,
                )
                html.close_td()
                html.close_tr()

            html.close_table()

        if not config.is_single_local_site():
            html.end_foldable_container()


sidebar_snapins["master_control"] = {
    "title" : _("Master Control"),
    "description" : _("Buttons for switching globally states such as enabling "
                      "checks and notifications"),
    "render" : render_master_control,
    "allowed" : [ "admin", ],
    "styles" : """
div.snapin table.master_control {
    width: 100%;
    margin: 0px 0px 0px 0px;
    border-spacing: 0px;
}

div.snapin table.master_control td div.toggle_switch {
    float: right;
}

div.snapin table.master_control td.left a {
    text-align: left;
    font-size: 8pt;
    font-weight: normal;
}

div.snapin table.master_control td.left {
    text-align: left;
}

div.snapin table.master_control td img.iconbutton {
    width: 60px;
    height: 16px;
}

"""
}

#.
#   .--Bookmark List-------------------------------------------------------.
#   | ____              _                         _      _     _     _     |
#   || __ )  ___   ___ | | ___ __ ___   __ _ _ __| | __ | |   (_)___| |_   |
#   ||  _ \ / _ \ / _ \| |/ / '_ ` _ \ / _` | '__| |/ / | |   | / __| __|  |
#   || |_) | (_) | (_) |   <| | | | | | (_| | |  |   <  | |___| \__ \ |_   |
#   ||____/ \___/ \___/|_|\_\_| |_| |_|\__,_|_|  |_|\_\ |_____|_|___/\__|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Shareable lists of bookmarks                                         |
#   '----------------------------------------------------------------------'

class BookmarkList(pagetypes.Overridable):
    @classmethod
    def type_name(self):
        return "bookmark_list"


    @classmethod
    def phrase(self, what):
        return {
            "title"          : _("Bookmark list"),
            "title_plural"   : _("Bookmark lists"),
            "add_to"         : _("Add to bookmark list"),
            "clone"          : _("Clone bookmark list"),
            "create"         : _("Create bookmark list"),
            "edit"           : _("Edit bookmark list"),
            "new"            : _("New list"),
        }.get(what, pagetypes.Base.phrase(what))


    @classmethod
    def parameters(self, clazz):
        vs_topic = TextUnicode(
            title = _("Topic") + "<sup>*</sup>",
            size = 50,
            allow_empty = False,
        )

        def bookmark_config_to_vs(v):
            if v:
                return (v["title"], v["url"], v["icon"], v["topic"])
            else:
                return v

        def bookmark_vs_to_config(v):
            return {
                "title" : v[0],
                "url"   : v[1],
                "icon"  : v[2],
                "topic" : v[3],
            }

        return [(_("Bookmarks"), [
            # sort-index, key, valuespec
            (2.5, "default_topic", TextUnicode(
                title = _("Default Topic") + "<sup>*</sup>",
                size = 50,
                allow_empty = False,
            )),
            (3.0, "bookmarks", ListOf(
                # For the editor we want a compact dialog. The tuple horizontal editin mechanism
                # is exactly the thing we want. But we want to store the data as dict. This is a
                # nasty hack to use the transform by default. Better would be to make Dict render
                # the same way the tuple is rendered.
                Transform(
                    Tuple(
                        elements = [
                            (TextUnicode(
                                title = _("Title") + "<sup>*</sup>",
                                size = 30,
                                allow_empty = False,
                            )),
                            (TextUnicode(
                                title = _("URL"),
                                size = 50,
                                allow_empty = False,
                            )),
                            (IconSelector(
                                title = _("Icon"),
                            )),
                            (Alternative(
                                elements = [
                                    FixedValue(None,
                                        title = _("Use default topic"),
                                        totext = _("(default topic)"),
                                    ),
                                    TextUnicode(
                                        title = _("Individual topic"),
                                        size = 30,
                                        allow_empty = False,
                                    ),
                                ],
                                title = _("Topic") + "<sup>*</sup>",
                                style = "dropdown",
                            )),
                        ],
                        orientation = "horizontal",
                        title = _("Bookmarks"),
                    ),
                    forth = bookmark_config_to_vs,
                    back = bookmark_vs_to_config,
                ),
            )),
        ])]


    @classmethod
    def _load(self):
        self.load_legacy_bookmarks()


    @classmethod
    def add_default_bookmark_list(cls):
        attrs = {
            "title"         : u"My Bookmarks",
            "public"        : False,
            "owner"         : config.user.id,
            "name"          : "my_bookmarks",
            "description"   : u"Your personal bookmarks",
            "default_topic" : u"My Bookmarks",
            "bookmarks"     : [],
        }

        cls.add_instance((config.user.id, "my_bookmarks"), cls(attrs))


    @classmethod
    def load_legacy_bookmarks(self):
        # Don't load the legacy bookmarks when there is already a my_bookmarks list
        if self.has_instance((config.user.id, "my_bookmarks")):
            return

        # Also don't load them when the user has at least one bookmark list
        for user_id, name in self.instances_dict().keys():
            if user_id == config.user.id:
                return

        self.add_default_bookmark_list()
        bookmark_list = self.instance((config.user.id, "my_bookmarks"))

        for title, url in load_legacy_bookmarks():
            bookmark_list.add_bookmark(title, url)


    @classmethod
    def new_bookmark(self, title, url):
        return {
           "title" : title,
           "url"   : url,
           "icon"  : None,
           "topic" : None,
        }


    def default_bookmark_topic(self):
        return self._["default_topic"]


    def bookmarks_by_topic(self):
        topics = {}
        for bookmark in self._["bookmarks"]:
            topic = topics.setdefault(bookmark["topic"], [])
            topic.append(bookmark)
        return sorted(topics.items())


    def add_bookmark(self, title, url):
        self._["bookmarks"].append(BookmarkList.new_bookmark(title, url))


pagetypes.declare(BookmarkList)


def load_legacy_bookmarks():
    path = config.user.confdir + "/bookmarks.mk"
    return store.load_data_from_file(path, [])


def save_legacy_bookmarks(bookmarks):
    config.user.save_file("bookmarks", bookmarks)


def get_bookmarks_by_topic():
    topics = {}
    BookmarkList.load()
    for instance in BookmarkList.instances_sorted():
        if (instance.is_mine() and instance.may_see()) or \
           (not instance.is_mine() and instance.is_public() and instance.may_see()):
            for topic, bookmarks in instance.bookmarks_by_topic():
                if topic == None:
                    topic = instance.default_bookmark_topic()
                bookmark_list = topics.setdefault(topic, [])
                bookmark_list += bookmarks
    return sorted(topics.items())


def render_bookmarks():
    html.javascript("""
function add_bookmark() {
    url = parent.frames[1].location;
    title = parent.frames[1].document.title;
    get_url("add_bookmark.py?title=" + encodeURIComponent(title)
            + "&url=" + encodeURIComponent(url), updateContents, "snapin_bookmarks");
}""")

    for topic, bookmarks in get_bookmarks_by_topic():
        html.begin_foldable_container("bookmarks", topic, False, topic)

        for bookmark in bookmarks:
            icon = bookmark["icon"]
            if not icon:
                icon = "kdict"

            iconlink(bookmark["title"], bookmark["url"], icon)

        html.end_foldable_container()

    begin_footnote_links()
    link(_("Add Bookmark"), "javascript:void(0)", onclick="add_bookmark()")
    link(_("Edit"), "bookmark_lists.py")
    end_footnote_links()


def try_shorten_url(url):
    referer = html.req.headers_in.get("Referer")
    if referer:
        ref_p = urlparse.urlsplit(referer)
        url_p = urlparse.urlsplit(url)

        # If http/https or user, pw, host, port differ, don't try to shorten
        # the URL to be linked. Simply use the full URI
        if ref_p.scheme == url_p.scheme and ref_p.netloc == url_p.netloc:
            # We try to remove http://hostname/some/path/check_mk from the
            # URI. That keeps the configuration files (bookmarks) portable.
            # Problem here: We have not access to our own URL, only to the
            # path part. The trick: we use the Referrer-field from our
            # request. That points to the sidebar.
            referer = ref_p.path
            url     = url_p.path
            if url_p.query:
                url += '?' + url_p.query
            removed = 0
            while '/' in referer and referer.split('/')[0] == url.split('/')[0]:
                referer = referer.split('/', 1)[1]
                url = url.split('/', 1)[1]
                removed += 1

            if removed == 1:
                # removed only the first "/". This should be an absolute path.
                url = '/' + url
            elif '/' in referer:
                # there is at least one other directory layer in the path, make
                # the link relative to the sidebar.py's topdir. e.g. for pnp
                # links in OMD setups
                url = '../' + url
    return url


def add_bookmark(title, url):
    BookmarkList.load()

    if not BookmarkList.has_instance((config.user.id, "my_bookmarks")):
        BookmarkList.add_default_bookmark_list()

    bookmarks = BookmarkList.instance((config.user.id, "my_bookmarks"))
    bookmarks.add_bookmark(title, try_shorten_url(url))
    bookmarks.save_user_instances()


def ajax_add_bookmark():
    title = html.var("title")
    url   = html.var("url")
    if title and url:
        add_bookmark(title, url)
    render_bookmarks()


sidebar_snapins["bookmarks"] = {
    "title" : _("Bookmarks"),
    "description" : _("A simple and yet practical snapin allowing to create "
                      "bookmarks to views and other content in the main frame"),
    "render" : render_bookmarks,
    "allowed": [ "user", "admin", "guest" ],
    "styles" : """
div.bookmark {
    width: 230px;
    max-width: 230px;
    overflow: hidden;
    text-overflow: ellipsis;
    -o-text-overflow: ellipsis;
    white-space: nowrap;
    color: white;
}
"""
}


#.
#   .--Custom Links--------------------------------------------------------.
#   |      ____          _                    _     _       _              |
#   |     / ___|   _ ___| |_ ___  _ __ ___   | |   (_)_ __ | | _____       |
#   |    | |  | | | / __| __/ _ \| '_ ` _ \  | |   | | '_ \| |/ / __|      |
#   |    | |__| |_| \__ \ || (_) | | | | | | | |___| | | | |   <\__ \      |
#   |     \____\__,_|___/\__\___/|_| |_| |_| |_____|_|_| |_|_|\_\___/      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def render_custom_links():
    links = config.custom_links.get(config.user.baserole_id)
    if not links:
        html.write_text((_("Please edit <tt>%s</tt> in order to configure which links are shown in this snapin.") %
                  (cmk.paths.default_config_dir + "/multisite.mk")) + "\n")
        return

    def render_list(ids, links):
        states = html.get_tree_states('customlinks')
        n = 0
        for entry in links:
            n += 1
            try:
                if type(entry[1]) == type(True):
                    idss = ids + [str(n)]
                    is_open = entry[1]
                    id = '/'.join(idss)
                    html.begin_foldable_container("customlinks", id, isopen=entry[1], title=entry[0])
                    render_list(idss, entry[2])
                    html.end_foldable_container()
                elif type(entry[1]) == str:
                    frame = len(entry) > 3 and entry[3] or "main"

                    if len(entry) > 2 and entry[2]:
                        icon_file = entry[2]

                        # Old configs used files named "link_<name>.gif". Those .gif files have
                        # been removed from Check_MK. Replacing such images with the default icon
                        if icon_file.endswith(".gif"):
                            icon_file = "icon_link.png"
                    else:
                        icon_file = "icon_link.png"

                    linktext = HTML(html.render_icon("images/%s" % icon_file) + " " + entry[0])

                    simplelink(linktext, entry[1], frame)
                else:
                    html.write_text(_("Second part of tuple must be list or string, not %s\n") % str(entry[1]))
            except Exception, e:
                html.write_text(_("invalid entry %s: %s<br>\n") % (entry, e))

    render_list([], links)

sidebar_snapins["custom_links"] = {
    "title" : _("Custom Links"),
    "description" : _("This snapin contains custom links which can be "
                      "configured via the configuration variable "
                      "<tt>custom_links</tt> in <tt>multisite.mk</tt>"),
    "render" : render_custom_links,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
#snapin_custom_links div.sublist {
    padding-left: 10px;
}
#snapin_custom_links img {
    margin-right: 5px;
}
#snapin_custom_links img.icon {
    width: 16px;
    height: 16px;
}
"""
}


#.
#   .--Dokuwiki------------------------------------------------------------.
#   |              ____        _                   _ _    _                |
#   |             |  _ \  ___ | | ___   ___      _(_) | _(_)               |
#   |             | | | |/ _ \| |/ / | | \ \ /\ / / | |/ / |               |
#   |             | |_| | (_) |   <| |_| |\ V  V /| |   <| |               |
#   |             |____/ \___/|_|\_\\__,_| \_/\_/ |_|_|\_\_|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#Example Sidebar:
#Heading1:
#   * [[link1]]
#   * [[link2]]
#
#----
#
#Heading2:
#   * [[link3]]
#   * [[link4]]

def render_wiki():
    filename = cmk.paths.omd_root + '/var/dokuwiki/data/pages/sidebar.txt'
    html.javascript("""
    function wiki_search()
    {
        var oInput = document.getElementById('wiki_search_field');
        top.frames["main"].location.href =
           "/%s/wiki/doku.php?do=search&id=" + escape(oInput.value);
    }
    """ % config.omd_site())

    html.open_form(id_="wiki_search", onsubmit="wiki_search();")
    html.input(id_="wiki_search_field", type_="text", name="wikisearch")
    html.icon_button("#", _("Search"), "wikisearch", onclick="wiki_search();")
    html.close_form()
    html.div('', id_="wiki_side_clear")

    start_ul = True
    ul_started = False
    try:
        title = None
        for line in file(filename).readlines():
            line = line.strip()
            if line == "":
                if ul_started == True:
                    html.end_foldable_container()
                    start_ul = True
                    ul_started = False
            elif line.endswith(":"):
                title = line[:-1]
            elif line == "----":
                pass
                # html.br()

            elif line.startswith("*"):
                if start_ul == True:
                    if title:
                         html.begin_foldable_container("wikisnapin", title, True, title, indent=True)
                    else:
                        html.open_ul()
                    start_ul = False
                    ul_started = True

                erg = re.findall('\[\[(.*)\]\]', line)
                if len(erg) == 0:
                    continue
                erg = erg[0].split('|')
                if len(erg) > 1:
                    link = erg[0]
                    name = erg[1]
                else:
                    link = erg[0]
                    name = erg[0]

                if link.startswith("http://") or link.startswith("https://"):
                    simplelink(name, link, "_blank")
                else:
                    erg = name.split(':')
                    if len(erg) > 0:
                        name = erg[-1]
                    else:
                        name = erg[0]
                    bulletlink(name, "/%s/wiki/doku.php?id=%s" % (config.omd_site(), link))

            else:
                html.write(line)

        if ul_started == True:
            html.close_ul()
    except IOError:
        sidebar = html.render_a("sidebar",
                                href="/%s/wiki/doku.php?id=%s" % (config.omd_site(), _("sidebar")),
                                target = "main")
        html.write_html("<p>To get a navigation menu, you have to create a %s in your wiki first.</p>"\
                                                                           % sidebar)

sidebar_snapins["wiki"] = {
    "title" : _("Wiki"),
    "description" : _("Shows the Wiki Navigation of the OMD Site"),
    "render" : render_wiki,
    "allowed" : [ "admin", "user", "guest" ],
    "styles" : """
    #snapin_container_wiki div.content {
        font-weight: bold;
        color: white;
    }

    #snapin_container_wiki div.content p {
        font-weight: normal;
    }

    #wiki_navigation {
        text-align: left;
    }

    #wiki_search {
        width: 232px;
        padding: 0;
    }

    #wiki_side_clear {
        clear: both;
    }

    #wiki_search img.iconbutton {
        width: 33px;
        height: 26px;
        margin-top: -25px;
        left: 196px;
        float: left;
        position: relative;
        z-index:100;
    }

    #wiki_search input {
        margin:  0;
        padding: 0px 5px;
        font-size: 8pt;
        width: 194px;
        height: 25px;
        background-image: url("images/quicksearch_field_bg.png");
        background-repeat: no-repeat;
        -moz-border-radius: 0px;
        border-style: none;
        float: left;
    }
    """
}

#.
#   .--Virt. Host Tree-----------------------------------------------------.
#   |  __     ___      _       _   _           _     _____                 |
#   |  \ \   / (_)_ __| |_    | | | | ___  ___| |_  |_   _| __ ___  ___    |
#   |   \ \ / /| | '__| __|   | |_| |/ _ \/ __| __|   | || '__/ _ \/ _ \   |
#   |    \ V / | | |  | |_ _  |  _  | (_) \__ \ |_    | || | |  __/  __/   |
#   |     \_/  |_|_|   \__(_) |_| |_|\___/|___/\__|   |_||_|  \___|\___|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def compute_tag_tree(taglist):
    try:
        sites.live().set_prepend_site(True)
        query = "GET hosts\n" \
                "Columns: host_name filename state num_services_ok num_services_warn " \
                "num_services_crit num_services_unknown custom_variables"
        hosts = sites.live().query(query)
    finally:
        sites.live().set_prepend_site(False)

    hosts.sort()

    def get_tag_group_value(groupentries, tags):
        for entry in groupentries:
            if entry[0] in tags:
                return entry[0], entry[1] # tag, title
        # Not found -> try empty entry
        for entry in groupentries:
            if entry[0] == None:
                return None, entry[1]

        # No empty entry found -> get default (i.e. first entry)
        return groupentries[0][:2]

    # Prepare list of host tag groups and topics
    taggroups = {}
    topics = {}
    for entry in config.wato_host_tags:
        grouptitle           = entry[1]
        if '/' in grouptitle:
            topic, grouptitle = grouptitle.split("/", 1)
            topics.setdefault(topic, []).append(entry)

        groupname            = entry[0]
        group                = entry[2]
        taggroups[groupname] = group

    tree = {}
    for site, host_name, wato_folder, state, num_ok, num_warn, num_crit, num_unknown, custom_variables in hosts:
        if wato_folder.startswith("/wato/"):
            folder_path = wato_folder[6:-9]
            folder_path_components = folder_path.split("/")
            if wato.Folder.folder_exists(folder_path):
                folder_titles = wato.get_folder_title_path(folder_path)[1:] # omit main folder
        else:
            folder_titles = []

        # make state reflect the state of the services + host
        have_svc_problems = False
        if state:
            state += 1 # shift 1->2 (DOWN->CRIT) and 2->3 (UNREACH->UNKNOWN)
        if num_crit:
            state = 2
            have_svc_problems = True
        elif num_unknown:
            if state != 2:
                state = 3
            have_svc_problems = True
        elif num_warn:
            if not state:
                state = 1
            have_svc_problems = True

        tags = custom_variables.get("TAGS", []).split()

        tree_entry = tree # Start at top node

        # Now go through the levels of the tree. Each level may either be
        # - a tag group id, or
        # - "topic:" plus the name of a tag topic. That topic should only contain
        #   checkbox tags, or:
        # - "folder:3", where 3 is the folder level (starting at 1)
        # The problem with the "topic" entries is, that a host may appear several
        # times!

        current_branches = [ tree ]

        for tag in taglist:
            new_current_branches = []
            for tree_entry in current_branches:
                if tag.startswith("topic:"):
                    topic = tag[6:]
                    if topic in topics: # Could have vanished
                        # Iterate over all host tag groups with that topic
                        for entry in topics[topic]:
                            grouptitle  = entry[1].split("/", 1)[1]
                            group       = entry[2]
                            for tagentry in group:
                                tag_value, tag_title = tagentry[:2]
                                if tag_value in tags:
                                    new_current_branches.append(tree_entry.setdefault((tag_title, tag_value), {}))

                elif tag.startswith("folder:"):
                    level = int(tag[7:])
                    if level <= len(folder_titles):
                        tag_title = folder_titles[level-1]
                        tag_value = "folder:%d:%s" % (level, folder_path_components[level-1])
                    else:
                        tag_title = _("Hosts in this folder")
                        tag_value = "folder:%d:" % level

                    new_current_branches.append(tree_entry.setdefault((tag_title, tag_value), {}))
                else:
                    if tag not in taggroups:
                        continue # Configuration error. User deleted tag group after configuring his tree
                    tag_value, tag_title = get_tag_group_value(taggroups[tag], tags)
                    new_current_branches.append(tree_entry.setdefault((tag_title, tag_value), {}))

            current_branches = new_current_branches

        for tree_entry in new_current_branches:
            if not tree_entry:
                tree_entry.update({
                    "_num_hosts" : 0,
                    "_state"     : 0,
                })
            tree_entry["_num_hosts"] += 1
            tree_entry["_svc_problems"] = tree_entry.get("_svc_problems", False) or have_svc_problems
            if state == 2 or tree_entry["_state"] == 2:
                tree_entry["_state"] = 2
            else:
                tree_entry["_state"] = max(state, tree_entry["_state"])

    return tree

def tag_tree_worst_state(tree):
    if not tree.values():
        return 3
    if "_state" in tree:
        return tree["_state"]
    else:
        states = map(tag_tree_worst_state, tree.values())
        for x in states:
            if x == 2:
                return 2
        return max(states)


def tag_tree_has_svc_problems(tree):
    if "_svc_problems" in tree:
        return tree["_svc_problems"]
    else:
        for x in tree.values():
            if tag_tree_has_svc_problems(x):
                return True
        return False


def tag_tree_url(taggroups, taglist, viewname):
    urlvars = [("view_name", viewname), ("filled_in", "filter")]
    if viewname == "svcproblems":
        urlvars += [ ("st1", "on"), ("st2", "on"), ("st3", "on") ]

    for nr, (group, tag) in enumerate(zip(taggroups, taglist)):
        if group.startswith("topic:"):
            # Find correct tag group for this tag
            for entry in config.wato_host_tags:
                for tagentry in entry[2]:
                    if tagentry[0] == tag: # Found our tag
                        taggroup = entry[0]
                        urlvars.append(("host_tag_%d_grp" % nr, taggroup))
                        urlvars.append(("host_tag_%d_op" % nr, "is"))
                        urlvars.append(("host_tag_%d_val" % nr, tag))
                        break
        elif group.startswith("folder:"):
            continue # handled later
        else:
            urlvars.append(("host_tag_%d_grp" % nr, group))
            urlvars.append(("host_tag_%d_op" % nr, "is"))
            urlvars.append(("host_tag_%d_val" % nr, tag or ""))

    folder_components = {}
    for tag in taglist:
        if tag.startswith("folder:"):
            level_text, component = tag[7:].split(":")
            level = int(level_text)
            folder_components[level] = component

    if folder_components:
        wato_path = []
        for i in range(max(folder_components.keys())):
            level = i + 1
            if level not in folder_components:
                wato_path.append("*")
            else:
                wato_path.append(folder_components[level])

        urlvars.append(("wato_folder", "/".join(wato_path)))

    return html.makeuri_contextless(urlvars, "view.py")

def tag_tree_bullet(state, path, leaf):
    code = '<div class="tagtree %sstatebullet state%d">&nbsp;</div>' % ((leaf and "leaf " or ""), state)
    if not leaf:
        code = '<a title="%s" href="javascript:virtual_host_tree_enter(\'%s\');">%s</a>' % \
           (_("Display the tree only below this node"), "|".join(path), code)
    return code + " "


def is_tag_subdir(path, cwd):
    if not cwd:
        return True
    elif not path:
        return False
    elif path[0] != cwd[0]:
        return False
    else:
        return is_tag_subdir(path[1:], cwd[1:])

def render_tag_tree_level(taggroups, path, cwd, title, tree):
    if not is_tag_subdir(path, cwd) and not is_tag_subdir(cwd, path):
        return

    if path != cwd and is_tag_subdir(path, cwd):
        bullet = tag_tree_bullet(tag_tree_worst_state(tree), path, False)
        if tag_tree_has_svc_problems(tree):
            bullet += html.render_icon_button(tag_tree_url(taggroups, path, "svcproblems"),
                                        _("Show the service problems contained in this branch"),
                                        "svc_problems", target="main")

        if path:
            html.begin_foldable_container("tag-tree", ".".join(map(str, path)),
                                          False, HTML(bullet + title))

    items = tree.items()
    items.sort()

    for nr, ((title, tag), subtree) in enumerate(items):
        subpath = path + [tag or ""]
        url = tag_tree_url(taggroups, subpath, "allhosts")
        if "_num_hosts" in subtree:
            title += " (%d)" % subtree["_num_hosts"]
        href = '<a target=main href="%s">%s</a>' % (url, html.attrencode(title))
        if "_num_hosts" in subtree:

            if is_tag_subdir(path, cwd):
                html.write(tag_tree_bullet(subtree["_state"], subpath, True))
                if subtree.get("_svc_problems"):
                    url = tag_tree_url(taggroups, subpath, "svcproblems")
                    html.icon_button(url, _("Show the service problems contained in this branch"),
                            "svc_problems", target="main")
                html.write(href)
                html.br()
        else:
            render_tag_tree_level(taggroups, subpath, cwd, href, subtree)

    if path and path != cwd and is_tag_subdir(path, cwd):
        html.end_foldable_container()

virtual_host_tree_js = """
function virtual_host_tree_changed(field)
{
    var tree_conf = field.value;
    // Then send the info to python code via ajax call for persistance
    get_url_sync('sidebar_ajax_tag_tree.py?conf=' + escape(tree_conf));
    refresh_single_snapin("tag_tree");
}

function virtual_host_tree_enter(path)
{
    get_url_sync('sidebar_ajax_tag_tree_enter.py?path=' + escape(path));
    refresh_single_snapin("tag_tree");
}
"""

def render_tag_tree():
    if not config.virtual_host_trees:
        url = 'wato.py?varname=virtual_host_trees&mode=edit_configvar'
        multisite = html.render_a("Multisite", href=url, target="main")
        html.write_html(_('You have not defined any virtual host trees. You can do this '
                          'in the global settings for %s.') % multisite)
        return

    tree_conf = config.user.load_file("virtual_host_tree", {"tree": 0, "cwd": {}})
    if type(tree_conf) == int:
        tree_conf = {"tree": tree_conf, "cwd":{}} # convert from old style

    trees = dict([ (tree["id"], tree) for tree in
                    wato.transform_virtual_host_trees(config.virtual_host_trees) ])

    choices = sorted([ (tree["id"], tree["title"]) for tree in trees.values() ],
                     key=lambda x: x[1])

    html.begin_form("vtree")

    cwd = tree_conf["cwd"].get(tree_conf["tree"])

    html.select("vtree", choices, "%s" % tree_conf["tree"], onchange='virtual_host_tree_changed(this)',
                attrs={"style": "width:210px" if cwd else None})

    # Give chance to change one level up, if we are in a subtree
    if cwd:
        upurl = "javascript:virtual_host_tree_enter('%s')" % "|".join(cwd[:-1])
        html.icon_button(upurl, _("Go up one tree level"), "back")

    html.br()
    html.end_form()
    html.final_javascript(virtual_host_tree_js)

    try:
        tag_groups = trees[tree_conf["tree"]]["tag_groups"]
    except KeyError:
        # Fallback to first host tree in case the wanted does not exist (anymore)
        tag_groups = trees[choices[0][0]]["tag_groups"]

    tree = compute_tag_tree(tag_groups)
    html.open_div(class_="tag_tree")
    render_tag_tree_level(tag_groups, [], cwd, _("Virtual Host Tree"), tree)
    html.close_div()

sidebar_snapins["tag_tree"] = {
    "title" : _("Virtual Host Tree"),
    "description" : _("This snapin shows tree views of your hosts based on their tag "
                      "classifications. You can configure which tags to use in your "
                      "global settings of Multisite."),
    "render" : render_tag_tree,
    "refresh" : True,
    "allowed" : [ "admin", "user", "guest" ],
    "styles" : """

#snapin_tag_tree select {
    background-color: #6DA1B8;
    border-color: #123A4A;
    color: #FFFFFF;
    font-size: 8pt;
    height: 19px;
    margin-bottom: 2px;
    margin-top: -2px;
    padding: 0;
    width: 230px;

    float: right;
    width: 100%;
}

#snapin_tag_tree form img.iconbutton {
    width: 16px;
    height: 16px;
    float: right;
    display: inline-box;
}

#snapin_tag_tree div.tag_tree {
    clear: both;
}

#snapin_tag_tree div.statebullet {
    position: relative;
    top: 3px;
    left: 1px;
    float: none;
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 0px;
    box-shadow: 0px 0px 0.7px #284850;
}

#snapin_tag_tree ul > div.statebullet.leaf {
    margin-left: 16px;
}

#snapin_tag_tree b {
    font-weight: normal;
}

#snapin_tag_tree {
    position: relative;
    top: 0px;
    left: 0px;
}
"""
}
