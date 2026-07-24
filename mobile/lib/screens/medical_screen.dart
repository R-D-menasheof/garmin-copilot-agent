import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/medical_upload.dart';
import '../providers/medical_provider.dart';
import '../services/document_picker.dart';

/// Medical documents screen — upload and list personal medical documents
/// (Phase 4b). Raw files are stored server-side; the owner extracts them.
class MedicalScreen extends StatefulWidget {
  const MedicalScreen({super.key});

  @override
  State<MedicalScreen> createState() => _MedicalScreenState();
}

class _MedicalScreenState extends State<MedicalScreen> {
  @override
  void initState() {
    super.initState();
    final medical = context.read<MedicalProvider>();
    Future.microtask(medical.loadDocuments);
  }

  Future<void> _startUpload() async {
    final picker = context.read<DocumentPicker>();
    final medical = context.read<MedicalProvider>();

    final source = await showModalBottomSheet<_PickSource>(
      context: context,
      builder: (_) => const _PickSourceSheet(),
    );
    if (source == null) return;

    final picked = source == _PickSource.camera
        ? await picker.pickFromCamera()
        : await picker.pickFile();
    if (picked == null) return;

    final ok = await medical.uploadDocument(picked);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? 'המסמך הועלה בהצלחה' : (medical.error ?? 'ההעלאה נכשלה')),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final medical = context.watch<MedicalProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('מסמכים רפואיים')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: medical.uploading ? null : _startUpload,
        icon: medical.uploading
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.upload_file),
        label: const Text('העלאת מסמך'),
      ),
      body: medical.loading
          ? const Center(child: CircularProgressIndicator())
          : medical.documents.isEmpty
              ? _EmptyState(onUpload: medical.uploading ? null : _startUpload)
              : RefreshIndicator(
                  onRefresh: () => medical.loadDocuments(),
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
                    itemCount: medical.documents.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, i) =>
                        _DocumentTile(doc: medical.documents[i]),
                  ),
                ),
    );
  }
}

enum _PickSource { camera, file }

class _PickSourceSheet extends StatelessWidget {
  const _PickSourceSheet();

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.photo_camera_outlined),
            title: const Text('צלם מסמך'),
            onTap: () => Navigator.pop(context, _PickSource.camera),
          ),
          ListTile(
            leading: const Icon(Icons.upload_file_outlined),
            title: const Text('בחר קובץ (PDF/תמונה)'),
            onTap: () => Navigator.pop(context, _PickSource.file),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onUpload});

  final VoidCallback? onUpload;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.folder_shared_outlined, size: 44),
            const SizedBox(height: 12),
            Text(
              'אין עדיין מסמכים רפואיים.\nהעלה בדיקת דם, סיכום ביקור או מרשם.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onUpload,
              icon: const Icon(Icons.upload_file),
              label: const Text('העלאת מסמך'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DocumentTile extends StatelessWidget {
  const _DocumentTile({required this.doc});

  final MedicalUpload doc;

  @override
  Widget build(BuildContext context) {
    final isPdf = doc.contentType == 'application/pdf';
    return ListTile(
      leading: Icon(isPdf ? Icons.picture_as_pdf_outlined : Icons.image_outlined),
      title: Text(doc.filename, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        '${_formatDate(doc.uploadedAt)} · ${_formatSize(doc.sizeBytes)}'
        '${doc.category.isNotEmpty ? ' · ${doc.category}' : ''}',
      ),
      trailing: doc.extracted
          ? const Tooltip(
              message: 'עובד ונותח',
              child: Icon(Icons.check_circle_outline, color: Colors.green),
            )
          : const Tooltip(
              message: 'ממתין לעיבוד',
              child: Icon(Icons.hourglass_empty, color: Colors.orange),
            ),
    );
  }

  static String _formatDate(DateTime dt) =>
      '${dt.day.toString().padLeft(2, '0')}/'
      '${dt.month.toString().padLeft(2, '0')}/${dt.year}';

  static String _formatSize(int bytes) {
    if (bytes >= 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    if (bytes >= 1024) return '${(bytes / 1024).toStringAsFixed(0)} KB';
    return '$bytes B';
  }
}
