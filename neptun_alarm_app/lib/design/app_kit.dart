/// Продуктові імена компонентів поверх існуючої Neptun design system.
/// Нові екрани імпортують цей файл; поступово вирівнюємо неймінг без масових рефакторів.
library;

import '../core/widgets/neptun_button.dart';
import '../core/widgets/neptun_empty_state.dart';
import '../core/widgets/neptun_error_state.dart';
import '../core/widgets/neptun_input.dart';
import '../core/widgets/neptun_tab_page_scaffold.dart';
import '../widgets/neptun_card.dart';

export '../core/widgets/neptun_button.dart';
export '../core/widgets/neptun_empty_state.dart';
export '../core/widgets/neptun_error_state.dart';
export '../core/widgets/neptun_input.dart';
export '../core/widgets/neptun_tab_page_scaffold.dart';
export '../widgets/neptun_card.dart';

typedef AppCard = NeptunCard;
typedef AppButton = NeptunButton;
typedef AppTextField = NeptunInput;
typedef AppTabScaffold = NeptunTabPageScaffold;
typedef AppEmptyState = NeptunEmptyState;
typedef AppErrorState = NeptunErrorState;
