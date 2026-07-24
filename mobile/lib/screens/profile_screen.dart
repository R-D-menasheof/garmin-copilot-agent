import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/profile.dart';
import '../providers/profile_provider.dart';

/// Profile view/edit screen (Phase 4). Personal fields are editable; auto-synced
/// wearable metrics (weight, VO2max, RHR, …) are shown read-only.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _nameCtrl = TextEditingController();
  final _dobCtrl = TextEditingController();
  final _heightCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  String? _sex;
  List<String> _goals = [];
  List<String> _dietary = [];
  List<Medication> _meds = [];
  List<Supplement> _supps = [];
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    final provider = context.read<ProfileProvider>();
    Future.microtask(provider.load);
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _dobCtrl.dispose();
    _heightCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  void _initFromProfile(Profile p) {
    _nameCtrl.text = p.displayName;
    _dobCtrl.text = p.dateOfBirth ?? '';
    _heightCtrl.text = p.heightCm != null ? p.heightCm.toString() : '';
    _notesCtrl.text = p.notes;
    _sex = p.sex;
    _goals = [...p.goals];
    _dietary = [...p.dietaryPreferences];
    _meds = [...p.currentMedications];
    _supps = [...p.supplements];
    _initialized = true;
  }

  Future<void> _save() async {
    final provider = context.read<ProfileProvider>();
    final changes = <String, dynamic>{
      'display_name': _nameCtrl.text.trim(),
      'date_of_birth':
          _dobCtrl.text.trim().isEmpty ? null : _dobCtrl.text.trim(),
      'sex': _sex,
      'height_cm': double.tryParse(_heightCtrl.text.trim()),
      'goals': _goals,
      'dietary_preferences': _dietary,
      'notes': _notesCtrl.text.trim(),
      'current_medications': _meds.map((m) => m.toJson()).toList(),
      'supplements': _supps.map((s) => s.toJson()).toList(),
    };
    final ok = await provider.save(changes);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? 'הפרופיל נשמר' : (provider.error ?? 'השמירה נכשלה')),
      ),
    );
  }

  Future<void> _pickDob() async {
    final current = DateTime.tryParse(_dobCtrl.text) ?? DateTime(1990, 1, 1);
    final picked = await showDatePicker(
      context: context,
      initialDate: current,
      firstDate: DateTime(1920),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        _dobCtrl.text =
            '${picked.year}-${picked.month.toString().padLeft(2, '0')}-'
            '${picked.day.toString().padLeft(2, '0')}';
      });
    }
  }

  Future<void> _addChip(List<String> target, String title) async {
    final value = await _promptText(title);
    if (value != null && value.isNotEmpty) {
      setState(() => target.add(value));
    }
  }

  Future<String?> _promptText(String title, {String initial = ''}) async {
    final ctrl = TextEditingController(text: initial);
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(controller: ctrl, autofocus: true),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('ביטול'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text('הוסף'),
          ),
        ],
      ),
    );
  }

  Future<void> _addMedication() async {
    final name = await _promptText('שם התרופה');
    if (name != null && name.isNotEmpty) {
      setState(() => _meds.add(Medication(name: name)));
    }
  }

  Future<void> _addSupplement() async {
    final name = await _promptText('שם התוסף');
    if (name != null && name.isNotEmpty) {
      setState(() => _supps.add(Supplement(name: name)));
    }
  }

  String _today() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}-'
        '${now.day.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ProfileProvider>();
    final profile = provider.profile;

    if (provider.loading && profile == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('הפרופיל שלי')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (profile == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('הפרופיל שלי')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(provider.error ?? 'לא נטענו נתונים'),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => context.read<ProfileProvider>().load(),
                child: const Text('נסה שוב'),
              ),
            ],
          ),
        ),
      );
    }

    if (!_initialized) _initFromProfile(profile);

    return Scaffold(
      appBar: AppBar(title: const Text('הפרופיל שלי')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: provider.saving ? null : _save,
        icon: provider.saving
            ? const SizedBox(
                width: 18, height: 18,
                child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.save_outlined),
        label: const Text('שמור'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
        children: [
          _sectionTitle('פרטים אישיים'),
          TextField(
            controller: _nameCtrl,
            decoration: const InputDecoration(labelText: 'שם'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _dobCtrl,
            readOnly: true,
            onTap: _pickDob,
            decoration: InputDecoration(
              labelText: 'תאריך לידה',
              suffixIcon: const Icon(Icons.calendar_today, size: 18),
              helperText: profile.ageYears != null
                  ? 'גיל: ${profile.ageYears}'
                  : null,
            ),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _sex,
            decoration: const InputDecoration(labelText: 'מין'),
            items: const [
              DropdownMenuItem(value: 'Male', child: Text('זכר')),
              DropdownMenuItem(value: 'Female', child: Text('נקבה')),
            ],
            onChanged: (v) => setState(() => _sex = v),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _heightCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'גובה (ס"מ)'),
          ),
          const SizedBox(height: 20),

          _sectionTitle('מטרות'),
          _chips(_goals, () => _addChip(_goals, 'הוסף מטרה')),
          const SizedBox(height: 20),

          _sectionTitle('העדפות תזונה'),
          _chips(_dietary, () => _addChip(_dietary, 'הוסף העדפה')),
          const SizedBox(height: 20),

          _sectionTitle('תרופות'),
          ..._meds.asMap().entries.map((e) => _medTile(e.key, e.value)),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: TextButton.icon(
              onPressed: _addMedication,
              icon: const Icon(Icons.add),
              label: const Text('הוסף תרופה'),
            ),
          ),
          const SizedBox(height: 12),

          _sectionTitle('תוספים'),
          ..._supps.asMap().entries.map((e) => _suppTile(e.key, e.value)),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: TextButton.icon(
              onPressed: _addSupplement,
              icon: const Icon(Icons.add),
              label: const Text('הוסף תוסף'),
            ),
          ),
          const SizedBox(height: 20),

          _sectionTitle('הערות'),
          TextField(
            controller: _notesCtrl,
            maxLines: 4,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              hintText: 'הרגלים, טריגרים, לוח זמנים…',
            ),
          ),
          const SizedBox(height: 24),

          _sectionTitle('נתונים מהשעון (לקריאה בלבד)'),
          _readOnlyGrid(profile),
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(text, style: Theme.of(context).textTheme.titleMedium),
      );

  Widget _chips(List<String> items, VoidCallback onAdd) => Wrap(
        spacing: 8,
        runSpacing: 4,
        children: [
          for (final item in items)
            Chip(
              label: Text(item),
              onDeleted: () => setState(() => items.remove(item)),
            ),
          ActionChip(
            avatar: const Icon(Icons.add, size: 18),
            label: const Text('הוסף'),
            onPressed: onAdd,
          ),
        ],
      );

  Widget _medTile(int index, Medication med) => ListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(med.name),
        subtitle: med.isStopped ? const Text('הופסק') : null,
        trailing: med.isStopped
            ? IconButton(
                icon: const Icon(Icons.delete_outline),
                tooltip: 'הסר',
                onPressed: () => setState(() => _meds.removeAt(index)),
              )
            : TextButton(
                onPressed: () => setState(
                    () => _meds[index] = med.copyWith(stopped: _today())),
                child: const Text('סמן כהופסק'),
              ),
      );

  Widget _suppTile(int index, Supplement supp) => ListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(supp.name),
        subtitle: supp.isStopped ? const Text('הופסק') : null,
        trailing: IconButton(
          icon: const Icon(Icons.delete_outline),
          tooltip: 'הסר',
          onPressed: () => setState(() => _supps.removeAt(index)),
        ),
      );

  Widget _readOnlyGrid(Profile p) {
    final items = <(String, String)>[
      if (p.weightKg != null) ('משקל', '${p.weightKg} ק"ג'),
      if (p.bodyFatPct != null) ('אחוז שומן', '${p.bodyFatPct}%'),
      if (p.bmi != null) ('BMI', '${p.bmi}'),
      if (p.vo2max != null) ('VO2max', '${p.vo2max}'),
      if (p.fitnessAge != null) ('גיל כושר', '${p.fitnessAge}'),
      if (p.restingHeartRate != null) ('RHR', '${p.restingHeartRate}'),
    ];
    if (items.isEmpty) {
      return const Text('אין עדיין נתונים מסונכרנים מהשעון.');
    }
    return Column(
      children: [
        for (final (label, value) in items)
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            title: Text(label),
            trailing: Text(value,
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
        if (p.devices.isNotEmpty)
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            title: const Text('מכשירים'),
            trailing: Text(p.devices.map((d) => d.name).join(', ')),
          ),
      ],
    );
  }
}
