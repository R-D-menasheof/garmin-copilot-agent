import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/favorite_meal.dart';
import '../models/meal_entry.dart';
import '../models/meal_template.dart';
import '../providers/favorites_provider.dart';
import '../providers/meal_provider.dart';
import '../providers/templates_provider.dart';
import '../services/image_service.dart';
import '../widgets/meal_card.dart';

/// Screen for logging meals — text input, camera, history.
class LogMealScreen extends StatefulWidget {
  const LogMealScreen({super.key});

  @override
  State<LogMealScreen> createState() => _LogMealScreenState();
}

class _LogMealScreenState extends State<LogMealScreen> {
  final _textController = TextEditingController();
  bool _analyzing = false;

  @override
  void initState() {
    super.initState();
    // Load today's meals from Azure on screen open
    Future.microtask(() {
      final provider = context.read<MealProvider>();
      provider.loadToday();
      provider.loadRecents(limit: 6);
      context.read<FavoritesProvider>().loadFavorites();
      context.read<TemplatesProvider>().loadTemplates();
    });
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  Future<void> _analyzeText() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    setState(() => _analyzing = true);
    try {
      final provider = context.read<MealProvider>();
      final meals = await provider.analyzeText(text);
      await _persistMeals(meals);
      _textController.clear();
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _analyzing = false);
    }
  }

  Future<void> _analyzeImage() async {
    setState(() => _analyzing = true);
    try {
      final imageBytes = await context.read<ImageService>().captureFromCamera();
      if (imageBytes == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('הצילום בוטל')),
          );
        }
        return;
      }

      // Ask for optional description
      String? description;
      if (mounted) {
        description = await _promptForText(
          title: 'תיאור הארוחה',
          label: 'תיאור (אופציונלי)',
          hint: 'למשל: שווארמה בפיתה עם חומוס',
          confirmLabel: 'ניתוח',
        );
      }

      final meals = await context.read<MealProvider>().analyzeImage(
        imageBytes,
        description: description,
      );
      await _persistMeals(meals);
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _analyzing = false);
    }
  }

  Future<String?> _promptForText({
    required String title,
    required String label,
    required String hint,
    required String confirmLabel,
    TextInputType? keyboardType,
    TextDirection textDirection = TextDirection.rtl,
  }) {
    return showDialog<String>(
      context: context,
      builder: (dialogContext) => _TextPromptDialog(
        title: title,
        label: label,
        hint: hint,
        confirmLabel: confirmLabel,
        keyboardType: keyboardType,
        textDirection: textDirection,
      ),
    );
  }

  Future<void> _lookupBarcode() async {
    final barcode = await _promptForText(
      title: 'חיפוש ברקוד',
      label: 'ברקוד',
      hint: 'הזן ברקוד',
      confirmLabel: 'חפש',
      keyboardType: TextInputType.number,
      textDirection: TextDirection.ltr,
    );

    if (!mounted || barcode == null || barcode.isEmpty) {
      return;
    }

    setState(() => _analyzing = true);
    try {
      final meals = await context.read<MealProvider>().lookupBarcode(barcode);
      await _persistMeals(meals);
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) {
        setState(() => _analyzing = false);
      }
    }
  }

  Future<void> _persistMeals(List<MealEntry> meals) async {
    if (meals.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('לא נמצאו מאכלים. נסה שוב.')),
        );
      }
      return;
    }

    final provider = context.read<MealProvider>();
    final loggedAt = DateTime.now();
    for (var index = 0; index < meals.length; index += 1) {
      await provider.addMealCopy(
        meals[index],
        timestamp: loggedAt.add(Duration(seconds: index)),
      );
    }

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('נוספו ${meals.length} פריטים ✓')),
      );
    }
  }

  Future<void> _addRecentMeal(MealEntry meal) async {
    try {
      await context.read<MealProvider>().addMealCopy(meal);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${meal.foodName} נוסף מהרשימה האחרונה ✓')),
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _addFavoriteMeal(FavoriteMeal favorite) async {
    try {
      await context.read<MealProvider>().addMealCopy(favorite.meal);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${favorite.displayName} נוסף מהמועדפים ✓')),
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _addTemplate(MealTemplate template) async {
    final mealProvider = context.read<MealProvider>();
    final now = DateTime.now();
    try {
      for (var index = 0; index < template.meals.length; index += 1) {
        await mealProvider.addMealCopy(
          template.meals[index],
          timestamp: now.add(Duration(minutes: index)),
        );
      }
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${template.name} נוספה כתבנית ✓')),
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _saveFavorite(MealEntry meal) async {
    try {
      await context.read<FavoritesProvider>().addFavoriteFromMeal(
            meal,
            label: meal.foodName,
          );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${meal.foodName} נשמר כמועדף ✓')),
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _saveTodayAsTemplate() async {
    final mealProvider = context.read<MealProvider>();
    if (mealProvider.todayMeals.isEmpty) {
      return;
    }

    final name = await _promptForText(
      title: 'שמירת תבנית',
      label: 'שם התבנית',
      hint: 'לדוגמה: ארוחת בוקר',
      confirmLabel: 'שמור',
    );

    if (!mounted || name == null || name.isEmpty) {
      return;
    }

    try {
      await context.read<TemplatesProvider>().addTemplate(
            name,
            mealProvider.todayMeals,
            notes: 'Saved from log screen',
          );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$name נשמרה כתבנית ✓')),
      );
    } catch (error) {
      _showError(error);
    }
  }

  Widget _buildChipSection({
    required String title,
    required List<Widget> chips,
  }) {
    if (chips.isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleSmall,
            textDirection: TextDirection.rtl,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: chips,
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  void _showError(Object error) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('שגיאה: $error'),
        backgroundColor: Theme.of(context).colorScheme.error,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MealProvider>();
    final favorites = context.watch<FavoritesProvider>();
    final templates = context.watch<TemplatesProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('רישום ארוחה')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    textDirection: TextDirection.rtl,
                    decoration: const InputDecoration(
                      hintText: 'מה אכלת? (לדוגמה: 2 תפוחים)',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _analyzeText(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: _analyzing ? null : _analyzeText,
                  icon: _analyzing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send),
                ),
                IconButton(
                  onPressed: _analyzing ? null : _analyzeImage,
                  icon: const Icon(Icons.camera_alt),
                ),
                IconButton(
                  onPressed: _analyzing ? null : _lookupBarcode,
                  icon: const Icon(Icons.qr_code_scanner),
                ),
              ],
            ),
          ),
          _buildChipSection(
            title: 'אחרונים',
            chips: provider.recentMeals
                .map(
                  (meal) => ActionChip(
                    label: Text(meal.foodName),
                    onPressed: _analyzing ? null : () => _addRecentMeal(meal),
                  ),
                )
                .toList(),
          ),
          _buildChipSection(
            title: 'מועדפים',
            chips: favorites.favorites
                .map(
                  (favorite) => ActionChip(
                    label: Text(favorite.displayName),
                    onPressed: _analyzing ? null : () => _addFavoriteMeal(favorite),
                  ),
                )
                .toList(),
          ),
          _buildChipSection(
            title: 'תבניות',
            chips: templates.templates
                .map(
                  (template) => ActionChip(
                    label: Text(template.name),
                    onPressed: _analyzing ? null : () => _addTemplate(template),
                  ),
                )
                .toList(),
          ),
          if (provider.todayMeals.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _saveTodayAsTemplate,
                  icon: const Icon(Icons.bookmark_add_outlined),
                  label: const Text('שמור כתבנית'),
                ),
              ),
            ),
          Expanded(
            child: ListView.builder(
              itemCount: provider.todayMeals.length,
              itemBuilder: (context, index) {
                return MealCard(
                  meal: provider.todayMeals[index],
                  index: index,
                  onDelete: (i) async {
                    final mealDay = provider.todayMeals[i].timestamp;
                    await provider.removeMeal(mealDay, i);
                    if (!mounted) {
                      return;
                    }
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('פריט נמחק')),
                    );
                  },
                  onEdit: (i, updated) async {
                    await provider.updateMeal(updated.timestamp, i, updated);
                    if (!mounted) {
                      return;
                    }
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('פריט עודכן ✓')),
                    );
                  },
                  onFavorite: _saveFavorite,
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _TextPromptDialog extends StatefulWidget {
  const _TextPromptDialog({
    required this.title,
    required this.label,
    required this.hint,
    required this.confirmLabel,
    this.keyboardType,
    this.textDirection = TextDirection.rtl,
  });

  final String title;
  final String label;
  final String hint;
  final String confirmLabel;
  final TextInputType? keyboardType;
  final TextDirection textDirection;

  @override
  State<_TextPromptDialog> createState() => _TextPromptDialogState();
}

class _TextPromptDialogState extends State<_TextPromptDialog> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: TextField(
        controller: _controller,
        keyboardType: widget.keyboardType,
        decoration: InputDecoration(
          labelText: widget.label,
          hintText: widget.hint,
        ),
        textDirection: widget.textDirection,
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('ביטול'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, _controller.text.trim()),
          child: Text(widget.confirmLabel),
        ),
      ],
    );
  }
}
