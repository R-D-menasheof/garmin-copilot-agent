import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/services/notification_handler.dart';

void main() {
  group('routeForMessageData', () {
    test('a report notification opens the review screen', () {
      expect(routeForMessageData({'type': 'report'}), '/review');
    });

    test('unknown or missing type returns null', () {
      expect(routeForMessageData({'type': 'other'}), isNull);
      expect(routeForMessageData(<String, dynamic>{}), isNull);
    });
  });
}
