#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "StreamVault-src")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Patch anchor missing [{label}] in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched: {label}")


# FAST XTREAM SYNC
policy = root / "data/src/main/java/com/streamvault/data/sync/XtreamLiveSyncPolicy.kt"
replace_once(
    policy,
    """        return when (syncReason) {\n            XtreamLiveSyncReason.BACKGROUND_STALE,\n            XtreamLiveSyncReason.MANUAL_SETTINGS -> EffectiveXtreamLiveSyncMethod.CATEGORY_BY_CATEGORY\n            XtreamLiveSyncReason.INITIAL_ONBOARDING,\n            XtreamLiveSyncReason.FOREGROUND -> EffectiveXtreamLiveSyncMethod.STREAM_ALL\n        }\n""",
    """        return when (syncReason) {\n            XtreamLiveSyncReason.BACKGROUND_STALE,\n            XtreamLiveSyncReason.MANUAL_SETTINGS,\n            XtreamLiveSyncReason.INITIAL_ONBOARDING,\n            XtreamLiveSyncReason.FOREGROUND -> EffectiveXtreamLiveSyncMethod.STREAM_ALL\n        }\n""",
    "manual/background live sync uses streamed full catalog",
)

profile = root / "data/src/main/java/com/streamvault/data/sync/CatalogSyncRuntimeProfile.kt"
replace_once(profile, "maxCategoryConcurrency = 1,", "maxCategoryConcurrency = if (snapshot.isTelevision) 4 else 1,", "low-tier TV fallback concurrency")
replace_once(profile, "maxCategoryConcurrency = 2,", "maxCategoryConcurrency = if (snapshot.isTelevision) 8 else 2,", "mid-tier TV fallback concurrency")
replace_once(profile, "maxCategoryConcurrency = Int.MAX_VALUE,", "maxCategoryConcurrency = if (snapshot.isTelevision) 12 else 16,", "high-tier bounded fallback concurrency")

sync_manager = root / "data/src/main/java/com/streamvault/data/sync/SyncManager.kt"
text = sync_manager.read_text(encoding="utf-8")
if "import kotlinx.coroutines.withTimeoutOrNull\n" not in text:
    text = text.replace("import kotlinx.coroutines.withContext\n", "import kotlinx.coroutines.withContext\nimport kotlinx.coroutines.withTimeoutOrNull\n", 1)
old_call = "syncEpgOnly(provider, onProgress)"
if old_call not in text:
    raise SystemExit("Patch anchor missing [EPG retry call] in SyncManager.kt")
text = text.replace(
    old_call,
    "withTimeoutOrNull(90_000L) { syncEpgOnly(provider, onProgress) } ?: progress(provider.id, onProgress, \"EPG retry timed out; keeping synced Live TV.\")",
    1,
)
sync_manager.write_text(text, encoding="utf-8")
print("patched: visible EPG retry hard cap")

epg_worker = root / "data/src/main/java/com/streamvault/data/sync/BackgroundEpgSyncWorker.kt"
replace_once(
    epg_worker,
    """                        Log.i(TAG, \"Scheduling retry for provider $providerId: EPG completed with retryable failure\")\n                        Result.retry()\n""",
    """                        Log.i(TAG, \"EPG had a retryable partial failure for provider $providerId\")\n                        if (runAttemptCount >= 1) Result.success() else Result.retry()\n""",
    "cap partial EPG retry loop",
)
replace_once(
    epg_worker,
    """                    } else if (shouldRetry(result.exception)) {\n                        Result.retry()\n""",
    """                    } else if (shouldRetry(result.exception)) {\n                        if (runAttemptCount >= 1) Result.success() else Result.retry()\n""",
    "cap transient EPG retry loop",
)
replace_once(epg_worker, "com.streamvault.domain.model.Result.Loading -> Result.retry()", "com.streamvault.domain.model.Result.Loading -> if (runAttemptCount >= 1) Result.success() else Result.retry()", "cap loading EPG retry loop")
replace_once(epg_worker, "if (shouldRetry(e)) Result.retry() else Result.failure()", "if (shouldRetry(e)) { if (runAttemptCount >= 1) Result.success() else Result.retry() } else Result.failure()", "cap exceptional EPG retry loop")

# ROOMIER LIVE-TV UI
home = root / "app/src/main/java/com/streamvault/app/ui/screens/home/HomeScreen.kt"
replace_once(home, "        272.dp\n    }\n    val channelSearchWidth", "        320.dp\n    }\n    val channelSearchWidth", "wider TV category sidebar")
replace_once(home, "        320.dp\n    } else if (isDenseMode) {\n        300.dp\n    } else {\n        340.dp", "        380.dp\n    } else if (isDenseMode) {\n        370.dp\n    } else {\n        400.dp", "wider channel list column")
replace_once(
    home,
    """    val channelRowHeight = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 92.dp\n        LiveTvChannelMode.COMPACT -> 54.dp\n        LiveTvChannelMode.PRO -> 52.dp\n    }\n    val channelListSpacing = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 8.dp\n        LiveTvChannelMode.COMPACT -> 2.dp\n        LiveTvChannelMode.PRO -> 2.dp\n    }\n""",
    """    val channelRowHeight = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 104.dp\n        LiveTvChannelMode.COMPACT -> 76.dp\n        LiveTvChannelMode.PRO -> 72.dp\n    }\n    val channelListSpacing = when (uiState.liveTvChannelMode) {\n        LiveTvChannelMode.COMFORTABLE -> 12.dp\n        LiveTvChannelMode.COMPACT -> 7.dp\n        LiveTvChannelMode.PRO -> 6.dp\n    }\n""",
    "larger channel rows and breathing room",
)

sidebar = root / "app/src/main/java/com/streamvault/app/ui/screens/home/HomeSidebarComponents.kt"
replace_once(sidebar, ".padding(vertical = 2.dp)", ".padding(vertical = 4.dp)", "more category row separation")
replace_once(sidebar, "Modifier.padding(horizontal = 12.dp, vertical = 10.dp)", "Modifier.padding(horizontal = 16.dp, vertical = 14.dp)", "larger category focus rows")
replace_once(sidebar, "style = MaterialTheme.typography.bodyMedium,\n                maxLines = 1,", "style = MaterialTheme.typography.titleSmall,\n                maxLines = 1,", "larger category labels")
text = sidebar.read_text(encoding="utf-8")
text = text.replace("        272.dp\n    }", "        320.dp\n    }")
sidebar.write_text(text, encoding="utf-8")

cards = root / "app/src/main/java/com/streamvault/app/ui/components/shell/AppMediaCards.kt"
replace_once(cards, "val contentPadding = if (isUltraCompact) 5.dp else 6.dp", "val contentPadding = if (isUltraCompact) 7.dp else 9.dp", "roomier live row vertical padding")
replace_once(cards, "val horizontalPadding = if (isUltraCompact) 8.dp else 10.dp", "val horizontalPadding = if (isUltraCompact) 10.dp else 14.dp", "roomier live row horizontal padding")
replace_once(cards, "val logoWidth = if (isDense) 42.dp else if (isUltraCompact) 46.dp else 52.dp", "val logoWidth = if (isDense) 48.dp else if (isUltraCompact) 54.dp else 64.dp", "larger channel logos")
replace_once(cards, "val contentSpacing = if (isUltraCompact) 8.dp else 10.dp", "val contentSpacing = if (isUltraCompact) 10.dp else 14.dp", "more live row spacing")
replace_once(cards, "style = if (isDense) MaterialTheme.typography.bodyLarge else MaterialTheme.typography.titleSmall,", "style = if (isDense) MaterialTheme.typography.titleSmall else MaterialTheme.typography.titleMedium,", "larger channel titles")
replace_once(cards, "style = if (isDense) MaterialTheme.typography.labelMedium else MaterialTheme.typography.bodySmall,", "style = if (isDense) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium,", "larger EPG text")


# PHONE-SAFE SETTINGS + UNLIMITED SERVER ENTRY
# The upstream TV-first settings surface can crash on some phones. Keep the
# full TV screen unchanged and route phones to a compact touch-first provider
# manager that always exposes ADD MORE SERVER.
app_navigation = root / "app/src/main/java/com/streamvault/app/navigation/AppNavigation.kt"
replace_once(
    app_navigation,
    """            SettingsScreen(
                onNavigate = { route -> tabNavigate(route) },
                onAddProvider = dropUnlessResumed {
                    navController.navigate(Routes.providerSetup(null))
                },
                onEditProvider = { provider ->
                    navController.navigateIfResumed(Routes.providerSetup(provider.id))
                },
                onNavigateToParentalControl = { providerId ->
                    navController.navigateIfResumed(Routes.parentalControlGroups(providerId))
                },
                currentRoute = Routes.SETTINGS,
                initialBackupImportUri = backupUri
            )
""",
    """            if (com.streamvault.app.device.rememberIsTelevisionDevice()) {
                SettingsScreen(
                    onNavigate = { route -> tabNavigate(route) },
                    onAddProvider = dropUnlessResumed {
                        navController.navigate(Routes.providerSetup(null))
                    },
                    onEditProvider = { provider ->
                        navController.navigateIfResumed(Routes.providerSetup(provider.id))
                    },
                    onNavigateToParentalControl = { providerId ->
                        navController.navigateIfResumed(Routes.parentalControlGroups(providerId))
                    },
                    currentRoute = Routes.SETTINGS,
                    initialBackupImportUri = backupUri
                )
            } else {
                com.streamvault.app.ui.screens.settings.MazenmiXPhoneSettingsScreen(
                    onNavigate = { route -> tabNavigate(route) },
                    onAddProvider = dropUnlessResumed {
                        navController.navigate(Routes.providerSetup(null))
                    },
                    onEditProvider = { provider ->
                        navController.navigateIfResumed(Routes.providerSetup(provider.id))
                    }
                )
            }
""",
    "phone settings uses touch-safe unlimited server manager",
)

phone_settings = root / "app/src/main/java/com/streamvault/app/ui/screens/settings/MazenmiXPhoneSettingsScreen.kt"
phone_settings.write_text(
    """package com.streamvault.app.ui.screens.settings

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.streamvault.domain.model.Provider

private val PhoneBackground = Color(0xFF07090D)
private val PhoneSurface = Color(0xFF141821)
private val PhoneAccent = Color(0xFF7C5CFC)
private val PhoneText = Color(0xFFF5F7FB)
private val PhoneMuted = Color(0xFFAAB1C0)
private val PhoneActive = Color(0xFF38D996)

@Composable
fun MazenmiXPhoneSettingsScreen(
    onNavigate: (String) -> Unit,
    onAddProvider: () -> Unit,
    onEditProvider: (Provider) -> Unit,
    viewModel: SettingsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    BackHandler { onNavigate("home") }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = PhoneBackground
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 18.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Settings",
                        color = PhoneText,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Servers and playlists",
                        color = PhoneMuted,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
                TextButton(onClick = { onNavigate("home") }) {
                    Text("DONE", color = PhoneText)
                }
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 28.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                item(key = "add-server-top") {
                    AddMoreServerButton(onAddProvider)
                }

                item(key = "server-heading") {
                    Column(modifier = Modifier.padding(top = 6.dp, bottom = 2.dp)) {
                        Text(
                            text = "MY SERVERS (${uiState.providers.size})",
                            color = PhoneText,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Add as many Xtream, M3U or portal servers as you want.",
                            color = PhoneMuted,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }

                if (uiState.providers.isEmpty()) {
                    item(key = "empty-servers") {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = PhoneSurface),
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(18.dp)) {
                                Text(
                                    text = "No server added",
                                    color = PhoneText,
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.SemiBold
                                )
                                Spacer(Modifier.height(6.dp))
                                Text(
                                    text = "Press ADD MORE SERVER to connect your first source.",
                                    color = PhoneMuted,
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }
                        }
                    }
                } else {
                    items(
                        items = uiState.providers,
                        key = { provider -> provider.id }
                    ) { provider ->
                        PhoneProviderCard(
                            provider = provider,
                            onEdit = { onEditProvider(provider) }
                        )
                    }

                    item(key = "add-server-bottom") {
                        Spacer(Modifier.height(4.dp))
                        AddMoreServerButton(onAddProvider)
                    }
                }
            }
        }
    }
}

@Composable
private fun AddMoreServerButton(onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp),
        shape = RoundedCornerShape(16.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = PhoneAccent,
            contentColor = Color.White
        )
    ) {
        Text(
            text = "＋  ADD MORE SERVER",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun PhoneProviderCard(
    provider: Provider,
    onEdit: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = PhoneSurface),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onEdit)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = provider.name,
                    color = PhoneText,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = provider.type.name.replace('_', ' '),
                    color = PhoneAccent,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = provider.serverUrl.ifBlank { "Server details saved" },
                    color = PhoneMuted,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = if (provider.isActive) "ACTIVE" else "SAVED",
                    color = if (provider.isActive) PhoneActive else PhoneMuted,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = "EDIT",
                    color = PhoneText,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
""",
    encoding="utf-8",
)
print("patched: phone-safe settings with unlimited ADD MORE SERVER actions")


# MAZENMIX TV BRANDING — force the launcher/app label in every resource set.
for strings in (root / "app/src/main/res").glob("values*/strings.xml"):
    data = strings.read_text(encoding="utf-8")
    data = data.replace("StreamVault", "MazenmiX TV").replace("Stream Vault", "MazenmiX TV")
    data = re.sub(r'<string name="app_name">.*?</string>', '<string name="app_name">MazenmiX TV</string>', data)
    strings.write_text(data, encoding="utf-8")

debug_strings = root / "app/src/debug/res/values/strings.xml"
if debug_strings.exists():
    data = debug_strings.read_text(encoding="utf-8")
    data = re.sub(r'<string name="app_name">.*?</string>', '<string name="app_name">MazenmiX TV</string>', data)
    debug_strings.write_text(data, encoding="utf-8")

print("MazenmiX TV patch complete")
