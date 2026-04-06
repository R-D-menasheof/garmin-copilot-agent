import 'dart:async';

import 'package:flutter/material.dart';

import '../models/meal_entry.dart';
import '../models/nutrition_source.dart';

/// Card displaying a single meal entry with edit/delete actions.
class MealCard extends StatelessWidget {
  final MealEntry meal;
  final int index;
  final Future<void> Function(int index)? onDelete;
  final Future<void> Function(int index, MealEntry updated)? onEdit;
  final Future<void> Function(MealEntry meal)? onFavorite;

  const MealCard({
    super.key,
    required this.meal,
    this.index = 0,
    this.onDelete,
    this.onEdit,
    this.onFavorite,
  });

  @override
  Widget build(BuildContext context) {
    return Dismissible(
      key: ValueKey('${meal.foodName}_${meal.timestamp}_$index'),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.only(left: 20),
        color: Theme.of(context).colorScheme.error,
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      confirmDismiss: (_) async {
        return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('מחיקת פריט'),
            content: Text('למחוק את ${meal.foodName}?'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('ביטול')),
              TextButton(
                onPressed: () => Navigator.pop(ctx, true),
                style: TextButton.styleFrom(foregroundColor: Theme.of(context).colorScheme.error),
                child: const Text('מחק'),
              ),
            ],
          ),
        ) ?? false;
      },
      onDismissed: (_) {
        if (onDelete != null) {
          unawaited(onDelete!(index));
        }
      },
      child: Card(
        child: ListTile(
          title: Text(meal.foodName),
          subtitle: Row(
            children: [
              Text(meal.portionDescription ?? ''),
              const SizedBox(width: 8),
              Text(
                'P:${meal.proteinG.toStringAsFixed(0)} C:${meal.carbsG.toStringAsFixed(0)} F:${meal.fatG.toStringAsFixed(0)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.outline,
                ),
              ),
            ],
          ),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '${meal.calories} kcal',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(width: 4),
              IconButton(
                icon: const Icon(Icons.star_border, size: 20),
                onPressed: onFavorite == null ? null : () => onFavorite!(meal),
                tooltip: 'שמור כמועדף',
              ),
              IconButton(
                icon: Icon(Icons.delete_outline, color: Theme.of(context).colorScheme.error, size: 20),
                onPressed: () async {
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text('מחיקת פריט'),
                      content: Text('למחוק את ${meal.foodName}?'),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('ביטול')),
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, true),
                          style: TextButton.styleFrom(foregroundColor: Theme.of(context).colorScheme.error),
                          child: const Text('מחק'),
                        ),
                      ],
                    ),
                  ) ?? false;
                  if (confirmed && onDelete != null) {
                    await onDelete!(index);
                  }
                },
                tooltip: 'מחק',
              ),
            ],
          ),
          onTap: () => _showEditDialog(context),
        ),
      ),
    );
  }

  void _showEditDialog(BuildContext context) {
    final caloriesCtrl = TextEditingController(text: meal.calories.toString());
    final proteinCtrl = TextEditingController(text: meal.proteinG.toStringAsFixed(1));
    final carbsCtrl = TextEditingController(text: meal.carbsG.toStringAsFixed(1));
    final fatCtrl = TextEditingController(text: meal.fatG.toStringAsFixed(1));
    final portionCtrl = TextEditingController(text: meal.portionDescription ?? '');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('עריכת ${meal.foodName}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: caloriesCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'קלוריות (kcal)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: proteinCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'חלבון (g)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: carbsCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'פחמימות (g)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: fatCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'שומן (g)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: portionCtrl,
                decoration: const InputDecoration(labelText: 'מנה'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('ביטול')),
          FilledButton(
            onPressed: () async {
              final updated = MealEntry(
                foodName: meal.foodName,
                calories: int.tryParse(caloriesCtrl.text) ?? meal.calories,
                proteinG: double.tryParse(proteinCtrl.text) ?? meal.proteinG,
                carbsG: double.tryParse(carbsCtrl.text) ?? meal.carbsG,
                fatG: double.tryParse(fatCtrl.text) ?? meal.fatG,
                fiberG: meal.fiberG,
                portionDescription: portionCtrl.text.isEmpty ? null : portionCtrl.text,
                source: meal.source,
                timestamp: meal.timestamp,
              );
              if (onEdit != null) {
                await onEdit!(index, updated);
              }
              Navigator.pop(ctx);
            },
            child: const Text('שמור'),
          ),
        ],
      ),
    );
  }
}
