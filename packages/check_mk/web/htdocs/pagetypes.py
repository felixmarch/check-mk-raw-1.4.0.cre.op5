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

# TODO: Cleanup "self" in classmethods to use "cls" which is
# a) easier to see that this is a classmethod
# b) more "standard" naming

import os, inspect
import config, table, forms, userdb
from lib import *
from valuespec import *
import cmk.store as store

try:
    import simplejson as json
except ImportError:
    import json

#   .--Base----------------------------------------------------------------.
#   |                        ____                                          |
#   |                       | __ )  __ _ ___  ___                          |
#   |                       |  _ \ / _` / __|/ _ \                         |
#   |                       | |_) | (_| \__ \  __/                         |
#   |                       |____/ \__,_|___/\___|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Base class of all things that are UserOverridable, ElementContainer |
#   |  or PageRenderer.                                                    |
#   '----------------------------------------------------------------------'

class Base(object):
    def __init__(self, d):
        super(Base, self).__init__()

        # The dictionary with the name _ holds all information about
        # the page in question - as a dictionary that can be loaded
        # and saved to files using repr().
        self._ = d

        # Now give all subclasses that chance to add mandatory keys
        # if they are missing
        for clazz in inspect.getmro(self.__class__)[::-1]:
            if "sanitize" in clazz.__dict__:
                clazz.sanitize(d)

    def internal_representation(self):
        return self._


    # You always must override the following method. Not all phrases
    # might be neccessary depending on the type of you page.
    # Possible phrases:
    # "title"        : Title of one instance
    # "title_plural" : Title in plural
    # "add_to"       : Text like "Add to foo bar..."
    # TODO: Look at GraphCollection for the complete list of phrases to
    # be defined for each page type and explain that here.
    @classmethod
    def phrase(self, phrase):
        return _("MISSING '%s'") % phrase

    # Implement this function in a subclass in order to add parameters
    # to be editable by the user when editing the details of such page
    # type. Note: This method does *not* use overriding, but all methods
    # of this name will be called in all inherited classes and concatenated.
    # Note:
    # - self is the original class, e.g. PageRenderer
    # - clazz is the derived class, e.g. GraphCollection
    # Returns a list of entries.
    # Each entry is a pair of a topic and a list of elements.
    # Each element is a triple of order, key and valuespec
    # TODO: Add topic here
    @classmethod
    def parameters(self, clazz):
        return [ ( _("General Properties"), [
            ( 1.1, 'name', ID(
                title = _('Unique ID'),
                help = _("The ID will be used do identify this page in URLs. If this page has the "
                         "same ID as a builtin page of the type <i>%s</i> then it will shadow the builtin one.") % self.phrase("title"),
            )),
            ( 1.2, 'title', TextUnicode(
                title = _('Title') + '<sup>*</sup>',
                size = 50,
                allow_empty = False,
            )),
            ( 1.3, 'description', TextAreaUnicode(
                title = _('Description') + '<sup>*</sup>',
                help = _("The description is optional and can be used for explanations or documentation"),
                rows = 4,
                cols = 50,
            )),
        ])]


    # Define page handlers for the neccessary pages. This is being called (indirectly)
    # in index.py. That way we do not need to hard code page handlers for all types of
    # PageTypes in plugins/pages. It is simply sufficient to register a PageType and
    # all page handlers will exist :-)
    # Do *not* override this. It collects all page handlers of our
    # page type by calling _page_handlers() for each class
    @classmethod
    def page_handlers(self):
        # Collect all page handlers from subclasses
        handlers = {}
        for clazz in inspect.getmro(self)[::-1]:
            if "_page_handlers" in clazz.__dict__:
                handlers.update(clazz._page_handlers(self))
        return handlers


    # Do *not* override this. It collects all editable parameters of our
    # page type by calling parameters() for each class
    @classmethod
    def collect_parameters(self):
        topics = {}
        for clazz in inspect.getmro(self)[::-1]:
            if "parameters" in clazz.__dict__:
                for topic, elements in clazz.parameters(self):
                    el = topics.setdefault(topic, [])
                    el += elements

        # Sort topics and elements in the topics
        for topic in topics.values():
            topic.sort()

        sorted_topics = topics.items()
        sorted_topics.sort(cmp = lambda t1, t2: cmp(t1[1][0], t2[1][0]))

        # Now remove order numbers. Also drop the topic completely
        # for the while
        # TODO: Reenable topic as soon as we have the first page type
        # with more than one topic
        parameters = []
        for topic, elements in sorted_topics:
            for _unused_order, key, vs in elements:
                parameters.append((key, vs))

        return parameters


    # Object methods that *can* be overridden - for cases where
    # that pages in question of a dictionary format that is not
    # compatible.
    def name(self):
        return self._["name"]


    def title(self):
        return self._["title"]


    def description(self):
        return self._.get("description", "")


    def is_hidden(self):
        return False


    def render_title(self):
        return _u(self.title())


    def is_empty(self):
        return False

    # Default values for the creation dialog can be overridden by the
    # sub class.
    @classmethod
    def default_name(self):
        stem = self.type_name()
        nr = 1
        while True:
            name = "%s_%d" % (stem, nr)
            conflict = False
            for instance in self.__instances.values():
                if instance.name() == name:
                    conflict = True
                    break
            if not conflict:
                return name
            else:
                nr += 1

    @classmethod
    def default_topic(self):
        return _("Other")

    # Store for all instances of this page type. The key into
    # this dictionary????
    # TODO: Brauchen wir hier überhaupt ein dict??
    __instances = {}

    @classmethod
    def clear_instances(self):
        self.__instances = {}

    @classmethod
    def add_instance(self, key, instance):
        self.__instances[key] = instance

    @classmethod
    def remove_instance(self, key):
        del self.__instances[key]

    # Return a list of all instances of this type
    @classmethod
    def instances(self):
        return self.__instances.values()

    @classmethod
    def instance(self, key):
        return self.__instances[key]

    @classmethod
    def has_instance(self, key):
        return key in self.__instances

    # Return a dict of all instances of this type
    @classmethod
    def instances_dict(self):
        return self.__instances

    # Return a list of pairs if instance key and instance, which
    # is sorted by the title of the instance
    @classmethod
    def instances_sorted(self):
        instances = self.__instances.values()
        instances.sort(cmp = lambda a,b: cmp(a.title(), b.title()))
        return instances

    # Stub function for the list of all pages. In case of Overridable
    # several instances might exist that overlay each other. This
    # function returns the final list of pages visible to the user
    @classmethod
    def pages(self):
        for instance in self.__instances.values():
            return instance


    # Stub function for finding a page by name. Overriden by
    # Overridable.
    @classmethod
    def find_page(self, name):
        for instance in self.__instances.values():
            if instance.name() == name:
                return instance


    @classmethod
    def type_name(self):
        raise NotImplementedError()


    # Lädt alle Dinge vom aktuellen User-Homeverzeichnis und
    # mergt diese mit den übergebenen eingebauten
    @classmethod
    def load(self):
        raise NotImplementedError()


    # Custom method to load e.g. old configs after performing the
    # loading of the regular files.
    @classmethod
    def _load(self):
        pass


#.
#   .--PageRenderer--------------------------------------------------------.
#   |   ____                  ____                _                        |
#   |  |  _ \ __ _  __ _  ___|  _ \ ___ _ __   __| | ___ _ __ ___ _ __     |
#   |  | |_) / _` |/ _` |/ _ \ |_) / _ \ '_ \ / _` |/ _ \ '__/ _ \ '__|    |
#   |  |  __/ (_| | (_| |  __/  _ <  __/ | | | (_| |  __/ | |  __/ |       |
#   |  |_|   \__,_|\__, |\___|_| \_\___|_| |_|\__,_|\___|_|  \___|_|       |
#   |              |___/                                                   |
#   +----------------------------------------------------------------------+
#   |  Base class for all things that have an URL and can be rendered as   |
#   |  an HTML page. And that can be added to the sidebar snapin of all    |
#   |  pages.
#   '----------------------------------------------------------------------'

class PageRenderer(Base):
    # Stuff to be overridden by the implementation of actual page types

    # TODO: Das von graphs.py rauspfluecken. Also alles, was man
    # überladen muss oder kann.

    # Attribute for identifying that page when building an URL to
    # the page. This is always "name", but
    # in the views it's for historic reasons "view_name". We might
    # change this in near future.
    # TODO: Change that. In views.py we could simply accept *both*.
    # First look for "name" and then for "view_name" if "name" is
    # missing.
    @classmethod
    def ident_attr(self):
        return "name"


    # Parameters special for page renderers. These can be added to the sidebar,
    # so we need a topic and a checkbox for the visibility
    @classmethod
    def parameters(self, clazz):
        return [(_("General Properties"), [
            ( 1.4, 'topic', TextUnicode(
                title = _('Topic') + '<sup>*</sup>',
                size = 50,
                allow_empty = False,
            )),
            ( 2.0, 'hidden', Checkbox(
                title = _("Sidebar integration"),
                label = _('Do not add a link to this page in sidebar'),
            )),
        ])]


    @classmethod
    def _page_handlers(self, clazz):
        return {
            clazz.type_name(): lambda: clazz.page_show(),
        }


    # Most important: page for showing the page ;-)
    @classmethod
    def page_show(cls):
        page = cls.requested_page()
        page.render()


    @classmethod
    def requested_page(cls):
        name = html.var(cls.ident_attr())
        cls.load()
        page = cls.find_page(name)
        if not page:
            raise MKGeneralException(_("Cannot find %s with the name %s") % (
                        cls.phrase("title"), name))
        return page


    # Links for the sidebar
    @classmethod
    def sidebar_links(self):
        for page in self.pages():
            if not page.is_empty() and not page.is_hidden():
                yield page.topic(), page.title(), page.page_url()


    def topic(self):
        return self._.get("topic", _("Other"))


    # Helper functions for page handlers and render function
    def page_header(self):
        return self.phrase("title") + " - " + self.title()


    def page_url(self):
        return html.makeuri_contextless([(self.ident_attr(), self.name())],
                                        filename = "%s.py" % self.type_name())


    def render_title(self):
        if not self.is_hidden():
            return HTML("<a href=\"%s\">%s</a>" %
                    (self.page_url(), html.attrencode(self.title())))
        else:
            return ""


#.
#   .--Overridable---------------------------------------------------------.
#   |         ___                      _     _       _     _               |
#   |        / _ \__   _____ _ __ _ __(_) __| | __ _| |__ | | ___          |
#   |       | | | \ \ / / _ \ '__| '__| |/ _` |/ _` | '_ \| |/ _ \         |
#   |       | |_| |\ V /  __/ |  | |  | | (_| | (_| | |_) | |  __/         |
#   |        \___/  \_/ \___|_|  |_|  |_|\__,_|\__,_|_.__/|_|\___|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Base class for things that the user can override by cloning and     |
#   |  editing and where the user might also create complete new types.    |
#   |  Examples: views, dashboards, graphs collections                     |
#   '----------------------------------------------------------------------'

class Overridable(Base):
    @classmethod
    def sanitize(self, d):
        d.setdefault("public", False)


    @classmethod
    def parameters(self, clazz):
        if clazz.has_overriding_permission("publish"):
            return [( _("General Properties"), [
                ( 2.2, 'public', Checkbox(
                    title = _("Visibility"),
                    label = _('Make available for all users')
                )),
            ])]
        else:
            return []


    @classmethod
    def _page_handlers(self, clazz):
        return {
            "%ss" % clazz.type_name()     : lambda: clazz.page_list(),
            "edit_%s" % clazz.type_name() : lambda: clazz.page_edit(),
        }


    def page_header(self):
        header = self.phrase("title") + " - " + self.title()
        if not self.is_mine():
            header += " (%s)" % self.owner()
        return header

    # Checks whether a page is publicly visible. This does not only need a flag
    # in the page itself, but also the permission from its owner to publish it.
    def is_public(self):
        return self._["public"] and (
            not self.owner() or config.user_may(self.owner(), "general.publish_" + self.type_name()))

    # Same, but checks if the owner has the permission to override builtin views
    def is_public_forced(self):
        return self.is_public() and \
          config.user_may(self.owner(), "general.force_" + self.type_name())


    def is_hidden(self):
        return self._.get("hidden", False)


    # Derived method for conveniance
    def is_builtin(self):
        return not self.owner()


    def is_mine(self):
        return self.owner() == config.user.id

    def owner(self):
        return self._["owner"]

    # Checks if the current user is allowed to see a certain page
    # TODO: Wie is die Semantik hier genau? Umsetzung vervollständigen!
    def may_see(self):
        perm_name = "%s.%s" % (self.type_name(), self.name())
        if config.permission_exists(perm_name) and not config.user.may(perm_name):
            return False

        # if self.owner() == "" and not config.user.may(perm_name):
        #    return False

        return True
        #    continue # not allowed to see this view

        # TODO: Permissions
        ### visual = visuals[(owner, visual_name)]
        ### if owner == config.user.id or \
        ###    (visual["public"] and owner != '' and config.user_may(owner, "general.publish_" + what)):
        ###     custom.append((owner, visual_name, visual))
        ### elif visual["public"] and owner == "":
        ###     builtin.append((owner, visual_name, visual))

    def may_delete(self):
        if self.is_builtin():
            return False
        elif self.is_mine():
            return True
        else:
            return config.user.may('general.delete_foreign_%s' % self.type_name())


    def may_edit(self):
        if self.is_builtin():
            return False
        elif self.is_mine():
            return True
        else:
            return config.user.may('general.edit_foreign_%s' % self.type_name())


    def edit_url(self):
        owner = not self.is_mine() and ("&owner=%s" % self.owner()) or ""
        return "edit_%s.py?load_name=%s%s" % (self.type_name(), self.name(), owner)


    def clone_url(self):
        backurl = html.urlencode(html.makeuri([]))
        return "edit_%s.py?load_user=%s&load_name=%s&mode=clone&back=%s" \
                    % (self.type_name(), self.owner(), self.name(), backurl)


    def delete_url(self):
        add_vars = [('_delete', self.name())]
        if not self.is_mine():
            add_vars.append(('_owner', self.owner()))
        return html.makeactionuri(add_vars)


    @classmethod
    def create_url(self):
        return "edit_%s.py?mode=create" % self.type_name()


    @classmethod
    def list_url(self):
        return "%ss.py" % self.type_name()


    def after_create_url(self):
        return None # where redirect after a create should go


    @classmethod
    def context_button_list(self):
        html.context_button(self.phrase("title_plural"), self.list_url(), self.type_name())

    def context_button_edit(self):
        html.context_button(_("Edit"), self.edit_url(), "edit")


    @classmethod
    def declare_overriding_permissions(self):
        config.declare_permission("general.edit_" + self.type_name(),
             _("Customize %s and use them") % self.phrase("title_plural"),
             _("Allows to create own %s, customize builtin %s and use them.") % (self.phrase("title_plural"), self.phrase("title_plural")),
             [ "admin", "user" ])

        config.declare_permission("general.publish_" + self.type_name(),
             _("Publish %s") % self.phrase("title_plural"),
             _("Make %s visible and usable for other users.") % self.phrase("title_plural"),
             [ "admin", "user" ])

        config.declare_permission("general.see_user_" + self.type_name(),
             _("See user %s") % self.phrase("title_plural"),
             _("Is needed for seeing %s that other users have created.") % self.phrase("title_plural"),
             [ "admin", "user", "guest" ])

        config.declare_permission("general.force_" + self.type_name(),
             _("Modify builtin %s") % self.phrase("title_plural"),
             _("Make own published %s override builtin %s for all users.") % (self.phrase("title_plural"), self.phrase("title_plural")),
             [ "admin" ])

        config.declare_permission("general.edit_foreign_" + self.type_name(),
             _("Edit foreign %s") % self.phrase("title_plural"),
             _("Allows to edit %s created by other users.") % self.phrase("title_plural"),
             [ "admin" ])

        config.declare_permission("general.delete_foreign_" + self.type_name(),
             _("Delete foreign %s") % self.phrase("title_plural"),
             _("Allows to delete %s created by other users.") % self.phrase("title_plural"),
             [ "admin" ])


    @classmethod
    def has_overriding_permission(self, how):
        return config.user.may("general.%s_%s" % (how, self.type_name()))


    @classmethod
    def need_overriding_permission(self, how):
        if not self.has_overriding_permission(how):
            raise MKAuthException(_("Sorry, you lack the permission. Operation: %s, table: %s") % (
                                    how, self.phrase("title_plural")))


    # Return all pages visible to the user, implements shadowing etc.
    @classmethod
    def pages(self):
        self.load()
        pages = {}

        # Builtin pages
        for page in self.instances():
            if page.is_public() and page.may_see() and page.is_builtin():
                pages[page.name()] = page

        # Public pages by normal other users
        for page in self.instances():
            if page.is_public() and page.may_see():
                pages[page.name()] = page

        # Public pages by admin users, forcing their versions over others
        for page in self.instances():
            if page.is_public() and page.may_see() and page.is_public_forced():
                pages[page.name()] = page

        # My own pages
        for page in self.instances():
            if page.is_mine() and config.user.may("general.edit_" + self.type_name()):
                pages[page.name()] = page

        return sorted(pages.values(), cmp = lambda a, b: cmp(a.title(), b.title()))


    @classmethod
    def page_choices(self):
        return [(page.name(), page.title()) for page in self.pages()]


    # Find a page by name, implements shadowing and
    # publishing und overriding by admins
    @classmethod
    def find_page(self, name):
        mine = None
        forced = None
        builtin = None
        foreign = None

        for page in self.instances():
            if page.name() != name:
                continue

            if page.is_mine() and config.user.may("general.edit_" + self.type_name()):
                mine = page

            elif page.is_public() and page.may_see():
                if page.is_public_forced():
                    forced = page
                elif page.is_builtin():
                    builtin = page
                else:
                    foreign = page

        if mine:
            return mine
        elif forced:
            return forced
        elif builtin:
            return builtin
        elif foreign:
            return foreign
        else:
            return None


    @classmethod
    def find_my_page(self, name):
        for page in self.instances():
            if page.is_mine() and page.name() == name:
                return page


    @classmethod
    def find_foreign_page(self, owner, name):
        try:
            return self.instance((owner, name))
        except KeyError:
            return None


    @classmethod
    def builtin_pages(self):
        return {}


    # Lädt alle Dinge vom aktuellen User-Homeverzeichnis und
    # mergt diese mit den übergebenen eingebauten
    @classmethod
    def load(self):
        self.clear_instances()

        # First load builtin pages. Set username to ''
        for name, page_dict in self.builtin_pages().items():
            page_dict["owner"]  = '' # might have been forgotten on copy action
            page_dict["public"] = True
            page_dict["name"]   = name
            new_page = self(page_dict)
            self.add_instance(("", name), new_page)

        # Now scan users subdirs for files "user_$type_name.mk"
        subdirs = os.listdir(config.config_dir)
        for user in subdirs:
            try:
                path = "%s/%s/user_%ss.mk" % (config.config_dir, user, self.type_name())
                if not os.path.exists(path):
                    continue

                if not userdb.user_exists(user):
                    continue

                user_pages = store.load_data_from_file(path, {})
                for name, page_dict in user_pages.items():
                    page_dict["owner"] = user
                    page_dict["name"] = name
                    self.add_instance((user, name), self(page_dict))

            except SyntaxError, e:
                raise MKGeneralException(_("Cannot load %s from %s: %s") %
                                                (self.type_name(), path, e))

        self._load()

        # Declare permissions - one for each of the pages, if it is public
        config.declare_permission_section(self.type_name(), self.phrase("title_plural"),
                                          do_sort = True)

        for instance in self.instances():
            if instance.is_public():
                self.declare_permission(instance)


    @classmethod
    def save_user_instances(self, owner=None):
        if not owner:
            owner = config.user.id

        save_dict = {}
        for page in self.instances():
            if page.owner() == owner:
                save_dict[page.name()] = page.internal_representation()

        config.save_user_file('user_%ss' % self.type_name(), save_dict, owner)


    @classmethod
    def add_page(self, new_page):
        self.add_instance((new_page.owner(), new_page.name()), new_page)


    def clone(self):
        page_dict = {}
        page_dict.update(self._)
        page_dict["owner"] = config.user.id
        new_page = self.__class__(page_dict)
        self.add_page(new_page)
        return new_page


    @classmethod
    def declare_permission(self, page):
        permname = "%s.%s" % (self.type_name(), page.name())
        if page.is_public() and not config.permission_exists(permname):
            config.declare_permission(permname, page.title(),
                             page.description(), ['admin','user','guest'])


    @classmethod
    def custom_list_buttons(self, instance):
        pass


    @classmethod
    def page_list(self):
        self.load()

        # custom_columns = []
        # render_custom_buttons = None
        # render_custom_columns = None
        # render_custom_context_buttons = None
        # check_deletable_handler = None

        self.need_overriding_permission("edit")

        html.header(self.phrase("title_plural"), stylesheets=["pages", "views", "status"])
        html.begin_context_buttons()
        html.context_button(self.phrase("new"), self.create_url(), "new_" + self.type_name())

        # TODO: Remove this legacy code as soon as views, dashboards and reports have been
        # moved to pagetypes.py
        html.context_button(_("Views"), "edit_views.py", "view")
        html.context_button(_("Dashboards"), "edit_dashboards.py", "dashboard")
        html.context_button(_("Reports"), "edit_reports.py", "report")

        ### if render_custom_context_buttons:
        ###     render_custom_context_buttons()

        for other_type_name, other_pagetype in page_types.items():
            if self.type_name() != other_type_name:
                html.context_button(other_pagetype.phrase("title_plural").title(), '%ss.py' % other_type_name, other_type_name)
        html.end_context_buttons()

        # Deletion
        delname  = html.var("_delete")
        if delname and html.transaction_valid():
            owner = html.var('_owner', config.user.id)
            if owner != config.user.id:
                self.need_overriding_permission("delete_foreign")

            instance = self.instance((owner, delname))

            try:
                if owner != config.user.id:
                    owned_by = _(" (owned by %s)") % owner
                else:
                    owned_by = ""
                c = html.confirm(_("Please confirm the deletion of \"%s\"%s.") % (
                  instance.title(), owned_by))
                if c:
                    self.remove_instance((owner, delname))
                    self.save_user_instances(owner)
                    html.reload_sidebar()
                elif c == False:
                    html.footer()
                    return
            except MKUserError, e:
                html.write("<div class=error>%s</div>\n" % e.message)
                html.add_user_error(e.varname, e.message)


        my_instances  = []
        foreign_instances  = []
        builtin_instances = []
        for instance in self.instances_sorted():
            if instance.may_see():
                if instance.is_builtin():
                    builtin_instances.append(instance)
                elif instance.is_mine():
                    my_instances.append(instance)
                elif instance.is_public() \
                     or instance.may_delete() or instance.may_edit():
                    foreign_instances.append(instance)

        for title, instances in [
            (_('Customized'),           my_instances),
            (_('Owned by other users'), foreign_instances),
            (_('Builtin'),              builtin_instances),
        ]:
            if not instances:
                continue

            html.write('<h3>' + title + '</h3>')

            table.begin(limit = None)
            for instance in instances:
                table.row()

                # Actions
                table.cell(_('Actions'), css = 'buttons visuals')

                # Clone / Customize
                buttontext = _("Create a customized copy of this")
                html.icon_button(instance.clone_url(), buttontext, "new_" + self.type_name())

                # Delete
                if instance.may_delete():
                    html.icon_button(instance.delete_url(), _("Delete!"), "delete")

                # Edit
                if instance.may_edit():
                    html.icon_button(instance.edit_url(), _("Edit"), "edit")

                self.custom_list_buttons(instance)

                # Internal ID of instance (we call that 'name')
                table.cell(_('ID'), instance.name(), css="narrow")

                # Title
                table.cell(_('Title'))
                html.write(html.attrencode(instance.render_title()))
                html.help(html.attrencode(_u(instance.description())))

                # Custom columns specific to that page type
                instance.render_extra_columns()

                ### for title, renderer in custom_columns:
                ###     table.cell(title, renderer(visual))

                # Owner
                if instance.is_builtin():
                    ownertxt = "<i>" + _("builtin") + "</i>"
                else:
                    ownertxt = instance.owner()
                table.cell(_('Owner'), ownertxt)
                table.cell(_('Public'), instance.is_public() and _("yes") or _("no"))
                table.cell(_('Hidden'), instance.is_hidden() and _("yes") or _("no"))

                # TODO: Haeeh? Another custom columns
                ### if render_custom_columns:
                ###     render_custom_columns(visual_name, visual)
            table.end()

        html.footer()
        return

    # Override this in order to display additional columns of an instance
    # in the table of all instances.
    def render_extra_columns(self):
        pass

    # Page for editing an existing page, or creating a new one
    @classmethod
    def page_edit(self):
        back_url = html.var("back", self.list_url())

        self.load()
        self.need_overriding_permission("edit")

        # Three possible modes:
        # "create" -> create completely new page
        # "clone"  -> like new, but prefill form with values from existing page
        # "edit"   -> edit existing page
        mode = html.var('mode', 'edit')
        if mode == "create":
            title = self.phrase("create")
            page_dict = {
                "name"  : self.default_name(),
                "topic" : self.default_topic(),
            }
        else:
            # Load existing page. visual from disk - and create a copy if 'load_user' is set
            page_name = html.var("load_name")
            if mode == "edit":
                title = self.phrase("edit")

                owner_user_id = html.var("owner", config.user.id)
                if owner_user_id == config.user.id:
                    page = self.find_my_page(page_name)
                else:
                    page = self.find_foreign_page(owner_user_id, page_name)

                if page == None:
                    raise MKUserError(None, _("The requested %s does not exist") % self.phrase("title"))

                # TODO FIXME: Looks like a hack
                self.remove_instance((owner_user_id, page_name)) # will be added later again
            else: # clone
                title = self.phrase("clone")
                load_user = html.var("load_user") # FIXME: Change varname to "owner"
                page = self.instance((load_user, page_name))
            page_dict = page.internal_representation()


        html.header(title) ### TODO: extra stylesheets for BI. Move bi.css into views.css , stylesheets=["pages", "views", "status", "bi"])
        html.begin_context_buttons()
        html.context_button(_("Back"), back_url, "back")
        html.end_context_buttons()

        # TODO: Implement multiple topics
        vs = Dictionary(
            title = _("General Properties"),
            render = 'form',
            optional_keys = None,
            elements = self.collect_parameters(),
        )

        def validate(page_dict):
            owner_user_id = html.var("owner", config.user.id)
            page_name = page_dict["name"]
            if owner_user_id == config.user.id:
                page = self.find_my_page(page_name)
            else:
                page = self.find_foreign_page(owner_user_id, page_name)
            if page:
                raise MKUserError("_p_name", _("You already have an element with the ID <b>%s</b>") % page_dict["name"])

        new_page_dict = forms.edit_valuespec(vs, page_dict, validate=validate, focus="_p_title", method="POST")
        if new_page_dict != None:
            # Take over keys from previous value that are specific to the page type
            # and not edited here.
            if mode in ("edit", "clone"):
                for key, value in page_dict.items():
                    new_page_dict.setdefault(key, value)

            owner = html.var("owner", config.user.id)
            new_page_dict["owner"] = owner
            new_page = self(new_page_dict)

            self.add_page(new_page)
            self.save_user_instances(owner)
            if mode == "create":
                redirect_url = new_page.after_create_url() or back_url
            else:
                redirect_url = back_url

            html.immediate_browser_redirect(0.5, redirect_url)
            html.message(_('Your changes haven been saved.'))
            # Reload sidebar.TODO: This code logically belongs to PageRenderer. How
            # can we simply move it there?
            # TODO: This is not true for all cases. e.g. the BookmarkList is not
            # of type PageRenderer but has a dedicated sidebar snapin. Maybe
            # the best option would be to make a dedicated method to decide whether
            # or not to reload the sidebar.
            if new_page_dict.get("hidden") in [ None, False ] \
               or new_page_dict.get("hidden") != page_dict.get("hidden"):
                html.reload_sidebar()

        else:
            html.show_localization_hint()

        html.footer()
        return




#.
#   .--Container-----------------------------------------------------------.
#   |              ____            _        _                              |
#   |             / ___|___  _ __ | |_ __ _(_)_ __   ___ _ __              |
#   |            | |   / _ \| '_ \| __/ _` | | '_ \ / _ \ '__|             |
#   |            | |__| (_) | | | | || (_| | | | | |  __/ |                |
#   |             \____\___/|_| |_|\__\__,_|_|_| |_|\___|_|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Base class for element containers - things that contain elements.   |
#   |  Examples: dashboards contain dashlets, graph collections contain    |
#   |  graphs.                                                             |
#   '----------------------------------------------------------------------'

class Container(Base):
    @classmethod
    def sanitize(self, d):
        d.setdefault("elements", [])

    # Which kind of elements are allowed to be added to this container?
    # Defaulting to all possible elements.
    @classmethod
    def may_contain(self, element_type_name):
        return True

    def elements(self):
        return self._["elements"]

    def add_element(self, element):
        self._["elements"].append(element)

    def move_element(self, nr, whither):
        el = self._["elements"][nr]
        del self._["elements"][nr]
        self._["elements"][whither:whither] = [ el ]

    def is_empty(self):
        return not self.elements()


class OverridableContainer(Overridable, Container):
    # The popup for "Add to ...", e.g. for adding a graph to a report
    # or dashboard. This is needed for page types with the aspect "ElementContainer".
    @classmethod
    def render_addto_popup(self, added_type):
        if not self.may_contain(added_type):
            return

        pages = self.pages()
        if pages:
            self.render_addto_popup_title(self.phrase("add_to"))
            for page in pages:
                self.render_addto_popup_entry(self.type_name(), page.name(), page.title())


    # Helper functions for layouting the add-to popup
    @classmethod
    def render_addto_popup_title(self, title):
        html.write('<li><span>%s:</span></li>' % title)


    @classmethod
    def render_addto_popup_entry(self, type_name, name, title):
        html.write("<li>")
        html.write("<a href=\"javascript:void(0)\" "
                   "onclick=\"pagetype_add_to_container('%s', '%s');reload_sidebar();\">" %
                    (type_name, name))
        html.render_icon(type_name)
        html.write(html.attrencode(title))
        html.write("</a>")
        html.write("</li>")


    # Callback for the Javascript function pagetype_add_to_container(). The
    # create_info will contain a dictionary that is known to the underlying
    # element. Note: this is being called with the base class object Container,
    # not with any actual subclass like GraphCollection. We need to find that
    # class by the URL variable page_type.
    @classmethod
    def ajax_add_element(self):
        page_type_name = html.var("page_type")
        page_name      = html.var("page_name")
        element_type   = html.var("element_type")
        create_info    = json.loads(html.var("create_info"))

        page_type = page_types[page_type_name]
        target_page, need_sidebar_reload = page_type.add_element_via_popup(page_name,
                                                            element_type, create_info)
        # Redirect user to tha page this displays the thing we just added to
        if target_page:
            if type(target_page) != str:
                target_page = target_page.page_url()
            html.write(target_page)
        html.write("\n%s" % (need_sidebar_reload and "true" or "false"))


    # Default implementation for generic containers - used e.g. by GraphCollection
    @classmethod
    def add_element_via_popup(self, page_name, element_type, create_info):
        self.need_overriding_permission("edit")

        need_sidebar_reload = False
        self.load()
        page = self.find_page(page_name)
        if not page.is_mine():
            page = page.clone()
            if isinstance(page, PageRenderer) and not page.is_hidden():
                need_sidebar_reload = True

        page.add_element(create_info) # can be overridden
        self.save_user_instances()
        return None, need_sidebar_reload
        # With a redirect directly to the page afterwards do it like this:
        # return page, need_sidebar_reload


#.
#   .--globals-------------------------------------------------------------.
#   |                         _       _           _                        |
#   |                    __ _| | ___ | |__   __ _| |___                    |
#   |                   / _` | |/ _ \| '_ \ / _` | / __|                   |
#   |                  | (_| | | (_) | |_) | (_| | \__ \                   |
#   |                   \__, |_|\___/|_.__/ \__,_|_|___/                   |
#   |                   |___/                                              |
#   +----------------------------------------------------------------------+
#   |  Global methods for the integration of PageTypes into Multisite      |
#   '----------------------------------------------------------------------'

# Global dict of all page types
page_types = {}

def declare(page_type):
    page_type.declare_overriding_permissions()
    page_types[page_type.type_name()] = page_type


def page_type(page_type_name):
    return page_types[page_type_name]


def has_page_type(page_type_name):
    return page_type_name in page_types


def all_page_types():
    return page_types


# Global module functions for the integration into the rest of the code

# index.py uses the following function in order to complete its
# page handler table
def page_handlers():
    page_handlers = {}
    for page_type in page_types.values():
        page_handlers.update(page_type.page_handlers())

    # Ajax handler for adding elements to a container
    # TODO: Shouldn't we move that declaration into the class?
    page_handlers["ajax_pagetype_add_element"] = lambda: OverridableContainer.ajax_add_element()
    return page_handlers


def render_addto_popup(added_type):
    for page_type in page_types.values():
        if issubclass(page_type, Container):
            page_type.render_addto_popup(added_type)
