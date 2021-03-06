# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import firefox_puppeteer.errors as errors

from marionette_driver import By, Wait
from marionette_driver.errors import NoSuchWindowException
from marionette_driver.keys import Keys

from firefox_puppeteer.ui.windows import BaseWindow
import firefox_puppeteer.errors as errors

from firefox_puppeteer.api.l10n import L10n
from firefox_puppeteer.decorators import use_class_as_property
from firefox_puppeteer.api.prefs import Preferences


class BrowserWindow(BaseWindow):
    """Representation of a browser window."""

    window_type = 'navigator:browser'

    dtds = [
        'chrome://branding/locale/brand.dtd',
        'chrome://browser/locale/aboutPrivateBrowsing.dtd',
        'chrome://browser/locale/browser.dtd',
        'chrome://browser/locale/netError.dtd',
    ]

    properties = [
        'chrome://branding/locale/brand.properties',
        'chrome://branding/locale/browserconfig.properties',
        'chrome://browser/locale/browser.properties',
        'chrome://browser/locale/preferences/preferences.properties',
        'chrome://global/locale/browser.properties',
    ]

    def __init__(self, *args, **kwargs):
        BaseWindow.__init__(self, *args, **kwargs)

        self._navbar = None
        self._tabbar = None

        # Timeout for loading remote web pages
        self.timeout_page_load = 30

    @property
    def default_homepage(self):
        """The default homepage as used by the current locale.

        :returns: The default homepage for the current locale.
        """
        return self._prefs.get_pref('browser.startup.homepage', interface='nsIPrefLocalizedString')

    @property
    def is_private(self):
        """Returns True if this is a Private Browsing window."""
        self.switch_to()

        with self.marionette.using_context('chrome'):
            return self.marionette.execute_script("""
                Components.utils.import("resource://gre/modules/PrivateBrowsingUtils.jsm");

                let chromeWindow = arguments[0].ownerDocument.defaultView;
                return PrivateBrowsingUtils.isWindowPrivate(chromeWindow);
            """, script_args=[self.window_element])

    @property
    def navbar(self):
        """Provides access to the navigation bar. This is the toolbar containing
        the back, forward and home buttons. It also contains the location bar.

        See the :class:`~ui.browser.toolbars.NavBar` reference.
        """
        self.switch_to()

        if not self._navbar:
            from .toolbars import NavBar

            navbar = self.window_element.find_element(By.ID, 'nav-bar')
            self._navbar = NavBar(lambda: self.marionette, self, navbar)

        return self._navbar

    @property
    def tabbar(self):
        """Provides access to the tab bar.

        See the :class:`~ui.browser.tabbar.TabBar` reference.
        """
        self.switch_to()

        if not self._tabbar:
            from .tabbar import TabBar

            tabbrowser = self.window_element.find_element(By.ID, 'tabbrowser-tabs')
            self._tabbar = TabBar(lambda: self.marionette, self, tabbrowser)

        return self._tabbar

    def close(self, trigger='menu', force=False):
        """Closes the current browser window by using the specified trigger.

        :param trigger: Optional, method to close the current browser window. This can
         be a string with one of `menu` or `shortcut`, or a callback which gets triggered
         with the current :class:`BrowserWindow` as parameter. Defaults to `menu`.

        :param force: Optional, forces the closing of the window by using the Gecko API.
         Defaults to `False`.
        """
        def callback(win):
            # Prepare action which triggers the opening of the browser window
            if callable(trigger):
                trigger(win)
            elif trigger == 'menu':
                # TODO: Make use of menubar class once it supports ids
                menu = win.marionette.find_element(By.ID, 'menu_closeWindow')
                menu.click()
            elif trigger == 'shortcut':
                win.send_shortcut(win.get_entity('closeCmd.key'),
                                  accel=True, shift=True)
            else:
                raise ValueError('Unknown closing method: "%s"' % trigger)

        BaseWindow.close(self, callback, force)

    def get_final_url(self, url):
        """Loads the page at `url` and returns the resulting url.

        This function enables testing redirects.

        :param url: The url to test.
        :returns: The resulting loaded url.
        """
        with self.marionette.using_context('content'):
            self.marionette.navigate(url)
            return self.marionette.get_url()

    def open_browser(self, trigger='menu', is_private=False):
        """Opens a new browser window by using the specified trigger.

        :param trigger: Optional, method in how to open the new browser window. This can
         be a string with one of `menu` or `shortcut`, or a callback which gets triggered
         with the current :class:`BrowserWindow` as parameter. Defaults to `menu`.

        :param is_private: Optional, if True the new window will be a private browsing one.

        :returns: :class:`BrowserWindow` instance for the new browser window.
        """
        def callback(win):
            # Prepare action which triggers the opening of the browser window
            if callable(trigger):
                trigger(win)
            elif trigger == 'menu':
                # TODO: Make use of menubar class once it supports ids
                menu_id = 'menu_newPrivateWindow' if is_private else 'menu_newNavigator'
                menu = win.marionette.find_element(By.ID, menu_id)
                menu.click()
            elif trigger == 'shortcut':
                cmd_key = 'privateBrowsingCmd.commandkey' if is_private else 'newNavigatorCmd.key'
                win.send_shortcut(win.get_entity(cmd_key),
                                  accel=True, shift=is_private)
            else:
                raise ValueError('Unknown opening method: "%s"' % trigger)

        return BaseWindow.open_window(self, callback, BrowserWindow)

    def open_about_window(self, trigger='menu'):
        """Opens the about window by using the specified trigger.

        :param trigger: Optional, method in how to open the new browser window. This can
         either the string `menu` or a callback which gets triggered
         with the current :class:`BrowserWindow` as parameter. Defaults to `menu`.

        :returns: :class:`AboutWindow` instance of the opened window.
        """
        def callback(win):
            # Prepare action which triggers the opening of the browser window
            if callable(trigger):
                trigger(win)
            elif trigger == 'menu':
                # TODO: Make use of menubar class once it supports ids
                menu = win.marionette.find_element(By.ID, 'aboutName')
                menu.click()
            else:
                raise ValueError('Unknown opening method: "%s"' % trigger)

        from ..about_window.window import AboutWindow
        return BaseWindow.open_window(self, callback, AboutWindow)

    def open_page_info_window(self, trigger='menu'):
        """Opens the page info window by using the specified trigger.

        :param trigger: Optional, method in how to open the new browser window. This can
         be a string with one of `menu` or `shortcut`, or a callback which gets triggered
         with the current :class:`BrowserWindow` as parameter. Defaults to `menu`.

        :returns: :class:`PageInfoWindow` instance of the opened window.
        """
        from ..pageinfo.window import PageInfoWindow

        def callback(win):
            # Prepare action which triggers the opening of the browser window
            if callable(trigger):
                trigger(win)
            elif trigger == 'menu':
                # TODO: Make use of menubar class once it supports ids
                menu = win.marionette.find_element(By.ID, 'menu_pageInfo')
                menu.click()
            elif trigger == 'shortcut':
                if win.marionette.session_capabilities['platform'] == 'WINNT':
                    raise ValueError('Page info shortcut not available on Windows.')
                win.send_shortcut(win.get_entity('pageInfoCmd.commandkey'),
                                  accel=True)
            elif trigger == 'context_menu':
                # TODO: Add once we can do right clicks
                pass
            else:
                raise ValueError('Unknown opening method: "%s"' % trigger)

        return BaseWindow.open_window(self, callback, PageInfoWindow)
