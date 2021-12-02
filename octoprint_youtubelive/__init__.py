# coding=utf-8
from __future__ import absolute_import
from typing import Container

import octoprint.plugin
from octoprint.server import user_permission
import docker

class youtubelive(octoprint.plugin.StartupPlugin,
				octoprint.plugin.TemplatePlugin,
				octoprint.plugin.AssetPlugin,
                octoprint.plugin.SettingsPlugin,
				octoprint.plugin.SimpleApiPlugin,
				octoprint.plugin.EventHandlerPlugin):
	
	def __init__(self):
		self.client = docker.from_env()
		self.container = None
	
	##~~ StartupPlugin
	
	def on_after_startup(self):
		self._logger.info("OctoPrint-YouTubeLive loaded! Checking stream status.")
		try:
			self.container = self.client.containers.get('YouTubeLive')
			self._logger.info("%s is streaming " % self.container.name)
			self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=True))
		except Exception as e:
			self._logger.error(str(e))
			self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))
	
	##~~ TemplatePlugin
	
	def get_template_configs(self):
		return [dict(type="settings",custom_bindings=False)]
		
	##~~ AssetPlugin
	
	def get_assets(self):
		return dict(
			js=["js/youtubelive.js"],
			css=["css/youtubelive.css"]
		)
		
	##~~ SettingsPlugin
	
	def get_settings_defaults(self):
		return dict(channel_id="",stream_id="",streaming=False,auto_start=False)
		
	##~~ SimpleApiPlugin
	
	def get_api_commands(self):
		return dict(startStream=[],stopStream=[],checkStream=[])
		
	def on_api_command(self, command, data):
		if not user_permission.can():
			from flask import make_response
			return make_response("Insufficient rights", 403)
		
		if command == 'startStream':
			self._logger.info("Start stream command received.")
			self.startStream()

		if command == 'stopStream':
			self._logger.info("Stop stream command received.")
			self.stopStream()

		if command == 'checkStream':
			self._logger.info("Checking stream status.")
			if self.container:
				self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=True))
			else:
				self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))
				
	##-- EventHandlerPlugin
	
	def on_event(self, event, payload):
		if event == "PrintStarted" and self._settings.get(["auto_start"]):
			self.startStream()
			
		if event in ["PrintDone","PrintCancelled"] and self._settings.get(["auto_start"]):
			self.stopStream()
			
	##-- Utility Functions
	
	def startStream(self):
		if not self.container:
			filters = []
			if self._settings.global_get(["webcam","flipH"]):
				filters.append("hflip")
			if self._settings.global_get(["webcam","flipV"]):
				filters.append("vflip")
			if self._settings.global_get(["webcam","rotate90"]):
				filters.append("transpose=cclock")
			if len(filters) == 0:
				filters.append("null")
			try:
				self.container = self.client.containers.run("octoprint/youtubelive:latest",command=[self._settings.get(["webcam_url"]),self._settings.get(["stream_id"]),"null",self._settings.get(["framerate"])],detach=True,privileged=False,devices=["/dev/vchiq"],name="YouTubeLive",auto_remove=True,network_mode="host")
				self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=True))
				self._logger.info(self._settings.get(["webcam_url"]))
				self._logger.info(self.container.logs())
			except Exception as e:
				self._plugin_manager.send_plugin_message(self._identifier, dict(error=str(e),status=True,streaming=False))
		return
		
	def stopStream(self):
		if self.container:
			try:
				self.container.stop()
				self.container = None
				self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))
			except Exception as e:
				self._plugin_manager.send_plugin_message(self._identifier, dict(error=str(e),status=True,streaming=False))
		else:
			self._plugin_manager.send_plugin_message(self._identifier, dict(status=True,streaming=False))

	##~~ Softwareupdate hook
	def get_update_information(self):
		return dict(
			youtubelive=dict(
				displayName="YouTube Live with more settings",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="moimart",
				repo="OctoPrint-YouTubeLive",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/moimart/OctoPrint-YouTubeLive/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "YouTube Live"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = youtubelive()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
