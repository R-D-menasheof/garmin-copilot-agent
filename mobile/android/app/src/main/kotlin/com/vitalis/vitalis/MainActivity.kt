package com.vitalis.vitalis

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity: FlutterFragmentActivity() {
	companion object {
		private const val CHANNEL = "vitalis/health_connect"
		private const val HEALTH_CONNECT_PACKAGE = "com.google.android.apps.healthdata"
		private const val HEALTH_CONNECT_SETTINGS_ACTION = "androidx.health.ACTION_HEALTH_CONNECT_SETTINGS"
	}

	override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
		super.configureFlutterEngine(flutterEngine)

		MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
			.setMethodCallHandler { call, result ->
				when (call.method) {
					"openHealthConnectSettings" -> {
						result.success(openHealthConnectSettings())
					}
					"openHealthConnectStore" -> {
						result.success(openHealthConnectStore())
					}
					else -> result.notImplemented()
				}
			}
	}

	private fun openHealthConnectSettings(): Boolean {
		val settingsIntent = Intent(HEALTH_CONNECT_SETTINGS_ACTION).apply {
			addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
		}
		val appInfoIntent = Intent(
			Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
			Uri.parse("package:$HEALTH_CONNECT_PACKAGE"),
		).apply {
			addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
		}

		return launchIntent(settingsIntent) ||
			launchPackageIntent() ||
			launchIntent(appInfoIntent)
	}

	private fun openHealthConnectStore(): Boolean {
		val marketIntent = Intent(
			Intent.ACTION_VIEW,
			Uri.parse("market://details?id=$HEALTH_CONNECT_PACKAGE"),
		).apply {
			addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
		}
		val webIntent = Intent(
			Intent.ACTION_VIEW,
			Uri.parse("https://play.google.com/store/apps/details?id=$HEALTH_CONNECT_PACKAGE"),
		).apply {
			addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
		}

		return launchIntent(marketIntent) || launchIntent(webIntent)
	}

	private fun launchPackageIntent(): Boolean {
		val intent = packageManager.getLaunchIntentForPackage(HEALTH_CONNECT_PACKAGE)?.apply {
			addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
		} ?: return false

		return launchIntent(intent)
	}

	private fun launchIntent(intent: Intent?): Boolean {
		if (intent == null) {
			return false
		}

		return try {
			if (intent.resolveActivity(packageManager) == null) {
				false
			} else {
				startActivity(intent)
				true
			}
		} catch (_: Exception) {
			false
		}
	}
}
