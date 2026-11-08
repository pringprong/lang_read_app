import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../data/bundle_reader.dart';
import '../data/db.dart';
import '../state/sync_provider.dart';

/// Sync tab (§6.4 / §10 / D-3): status card, import from desktop, export
/// results.
class SyncScreen extends StatelessWidget {
  const SyncScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final db = context.read<AppDb>();
    final sync = context.watch<SyncState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Sync with desktop')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _StatusCard(db: db, sync: sync),
          const SizedBox(height: 16),
          if (sync.importing || sync.exporting)
            const LinearProgressIndicator(minHeight: 4),
          if (sync.importing || sync.exporting) const SizedBox(height: 16),
          FilledButton.icon(
            icon: const Icon(Icons.download),
            label: const Text('Import from desktop'),
            onPressed: sync.importing || sync.exporting
                ? null
                : () => _import(context, sync),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            icon: const Icon(Icons.upload),
            label: const Text('Export results'),
            onPressed: sync.importing || sync.exporting
                ? null
                : () => _export(context, sync),
          ),
          const SizedBox(height: 16),
          if (sync.lastError != null)
            Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Icon(Icons.error_outline,
                        color: Theme.of(context).colorScheme.onErrorContainer),
                    const SizedBox(width: 8),
                    Expanded(child: Text(sync.lastError!)),
                  ],
                ),
              ),
            ),
          if (sync.lastImportStats != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text('Last import: ${sync.lastImportStats}'),
              ),
            ),
          const SizedBox(height: 24),
          Text(
            'How it works\n'
            '1. On the desktop: Sync → export bundle, copy sync-v1.zip to '
            'this phone (e.g. Downloads).\n'
            '2. Here: "Import from desktop", pick the zip. Content is '
            'verified and backed up before replacing local data.\n'
            '3. Review lessons on this phone. Results queue up offline.\n'
            '4. Here: "Export results", share/save results-*.zip, copy it '
            'to the desktop, and import it there.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Future<void> _import(BuildContext context, SyncState sync) async {
    final files = await FilePicker.pickFiles(
      dialogTitle: 'Pick a sync bundle (sync-v1.zip)',
      type: FileType.custom,
      allowedExtensions: const ['zip'],
    );
    if (files.isEmpty) return;
    final path = files.first.path;
    if (path == null || !context.mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Import content?'),
        content: const Text(
            'This replaces all local content (topics, lessons, words).\n'
            'A backup of the current database is created first.\n'
            'Pending review results are kept.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Import')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final stats = await sync.importBundle(path);
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Import complete'),
          content: Text(
              'Topics: ${stats.topics}\n'
              'Lessons: ${stats.lessons} (${stats.audioFiles} with audio)\n'
              'Sentences: ${stats.sentences}\n'
              'Words: ${stats.words}\n'
              'Pending results kept: ${stats.pendingKept}'
              '${stats.backupPath != null ? '\nBackup: ${stats.backupPath}' : ''}'),
          actions: [
            FilledButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK')),
          ],
        ),
      );
    } on BundleException catch (e) {
      // The error card on the sync screen shows sync.lastError.
      debugPrint('import failed: $e');
    }
  }

  Future<void> _export(BuildContext context, SyncState sync) async {
    try {
      final file = await sync.exportResults();
      if (!context.mounted) return;
      if (file == null) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('No pending results — nothing to sync back yet.')));
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Bundle saved:\n${file.path}'),
        duration: const Duration(seconds: 4),
      ));
      await SharePlus.instance.share(ShareParams(
        files: [XFile(file.path)],
        title: 'LangRead results bundle',
      ));
    } on BundleException catch (e) {
      debugPrint('export failed: $e');
    }
  }
}

class _StatusCard extends StatelessWidget {
  final AppDb db;
  final SyncState sync;

  const _StatusCard({required this.db, required this.sync});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            FutureBuilder<String?>(
              future: db.getMeta('last_import_at'),
              builder: (context, snapshot) =>
                  _row('Last import', snapshot.data ?? 'never'),
            ),
            StreamBuilder<int>(
              stream: db.watchPendingCount(),
              builder: (context, snapshot) =>
                  _row('Pending results', '${snapshot.data ?? 0} events'),
            ),
            _row('Storage', sync.baseDir.path),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(label,
                style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
