import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../providers/plan_provider.dart';
import '../providers/templates_provider.dart';

class MealPlanScreen extends StatefulWidget {
  const MealPlanScreen({super.key, this.initialDate});

  final DateTime? initialDate;

  @override
  State<MealPlanScreen> createState() => _MealPlanScreenState();
}

class _MealPlanScreenState extends State<MealPlanScreen> {
  late DateTime _selectedDate;
  final TextEditingController _notesController = TextEditingController();
  Set<String> _selectedTemplateIds = <String>{};

  @override
  void initState() {
    super.initState();
    _selectedDate = _dateOnly(widget.initialDate ?? DateTime.now());
    Future.microtask(_loadSelectedDate);
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadSelectedDate() async {
    final templatesProvider = context.read<TemplatesProvider>();
    final planProvider = context.read<PlanProvider>();

    if (templatesProvider.templates.isEmpty) {
      await templatesProvider.loadTemplates();
    }
    await planProvider.loadPlanDay(_selectedDate);

    if (!mounted) {
      return;
    }

    final plan = planProvider.currentPlan;
    setState(() {
      _selectedTemplateIds = {...?plan?.templateIds};
      _notesController.text = plan?.notes ?? '';
    });
  }

  Future<void> _changeDay(int deltaDays) async {
    setState(() {
      _selectedDate = _dateOnly(_selectedDate.add(Duration(days: deltaDays)));
    });
    await _loadSelectedDate();
  }

  Future<void> _savePlan() async {
    await context.read<PlanProvider>().savePlanDay(
          _selectedDate,
          templateIds: _selectedTemplateIds.toList(),
          notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
        );
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('התוכנית נשמרה ✓')),
    );
  }

  Future<void> _copyGroceryList(String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('רשימת הקניות הועתקה ✓')),
    );
  }

  DateTime _dateOnly(DateTime day) => DateTime(day.year, day.month, day.day);

  String _formatDate(DateTime day) =>
      '${day.day.toString().padLeft(2, '0')}/${day.month.toString().padLeft(2, '0')}/${day.year}';

  @override
  Widget build(BuildContext context) {
    final templatesProvider = context.watch<TemplatesProvider>();
    final planProvider = context.watch<PlanProvider>();
    final groceryLines = planProvider.groceryLines(
      templatesProvider.templates,
      templateIds: _selectedTemplateIds.toList(),
    );
    final groceryExport = planProvider.buildGroceryExport(
      templatesProvider.templates,
      templateIds: _selectedTemplateIds.toList(),
    );

    return Scaffold(
      appBar: AppBar(title: const Text('תכנון יום')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  IconButton(
                    onPressed: () => _changeDay(-1),
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Expanded(
                    child: Text(
                      _formatDate(_selectedDate),
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  IconButton(
                    onPressed: () => _changeDay(1),
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'תבניות ליום הזה',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  if (templatesProvider.templates.isEmpty && !templatesProvider.loading)
                    const Text('אין תבניות זמינות עדיין')
                  else if (templatesProvider.loading || planProvider.loading)
                    const Center(child: CircularProgressIndicator())
                  else
                    ...templatesProvider.templates.map(
                      (template) => CheckboxListTile(
                        value: _selectedTemplateIds.contains(template.id),
                        contentPadding: EdgeInsets.zero,
                        title: Text(template.name),
                        subtitle: Text('${template.meals.length} פריטים'),
                        onChanged: (selected) {
                          setState(() {
                            if (selected ?? false) {
                              _selectedTemplateIds.add(template.id);
                            } else {
                              _selectedTemplateIds.remove(template.id);
                            }
                          });
                        },
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'הערות',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _notesController,
                    maxLines: 3,
                    textDirection: TextDirection.rtl,
                    decoration: const InputDecoration(
                      hintText: 'למשל: יום אימון, ארוחה מחוץ לבית',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: planProvider.loading ? null : _savePlan,
                    icon: const Icon(Icons.save_outlined),
                    label: const Text('שמור תוכנית'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'רשימת קניות',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                      TextButton.icon(
                        onPressed: groceryLines.isEmpty ? null : () => _copyGroceryList(groceryExport),
                        icon: const Icon(Icons.copy_all_outlined),
                        label: const Text('העתק'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  if (groceryLines.isEmpty)
                    const Text('אין פריטים ברשימת הקניות')
                  else
                    ...groceryLines.map((line) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Text(line),
                        )),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}