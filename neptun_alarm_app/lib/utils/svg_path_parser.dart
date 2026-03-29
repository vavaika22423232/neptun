import 'dart:ui';

/// SVG Path parser - converts SVG path data to Flutter Path
class SvgPathParser {
  /// Parse SVG path data string to Flutter Path
  static Path parsePath(String pathData) {
    final path = Path();
    final commands = _tokenize(pathData);
    
    double currentX = 0;
    double currentY = 0;
    double startX = 0;
    double startY = 0;
    String lastCommand = '';
    double lastControlX = 0;
    double lastControlY = 0;
    
    int i = 0;
    while (i < commands.length) {
      String cmd = commands[i];
      
      // If it's a number, repeat the last command
      if (_isNumber(cmd)) {
        cmd = lastCommand;
      } else {
        i++;
      }
      
      switch (cmd) {
        case 'M': // Move to absolute
          currentX = double.parse(commands[i++]);
          currentY = double.parse(commands[i++]);
          path.moveTo(currentX, currentY);
          startX = currentX;
          startY = currentY;
          lastCommand = 'L'; // Subsequent coords are lineTo
          break;
          
        case 'm': // Move to relative
          currentX += double.parse(commands[i++]);
          currentY += double.parse(commands[i++]);
          path.moveTo(currentX, currentY);
          startX = currentX;
          startY = currentY;
          lastCommand = 'l';
          break;
          
        case 'L': // Line to absolute
          currentX = double.parse(commands[i++]);
          currentY = double.parse(commands[i++]);
          path.lineTo(currentX, currentY);
          lastCommand = 'L';
          break;
          
        case 'l': // Line to relative
          currentX += double.parse(commands[i++]);
          currentY += double.parse(commands[i++]);
          path.lineTo(currentX, currentY);
          lastCommand = 'l';
          break;
          
        case 'H': // Horizontal line absolute
          currentX = double.parse(commands[i++]);
          path.lineTo(currentX, currentY);
          lastCommand = 'H';
          break;
          
        case 'h': // Horizontal line relative
          currentX += double.parse(commands[i++]);
          path.lineTo(currentX, currentY);
          lastCommand = 'h';
          break;
          
        case 'V': // Vertical line absolute
          currentY = double.parse(commands[i++]);
          path.lineTo(currentX, currentY);
          lastCommand = 'V';
          break;
          
        case 'v': // Vertical line relative
          currentY += double.parse(commands[i++]);
          path.lineTo(currentX, currentY);
          lastCommand = 'v';
          break;
          
        case 'C': // Cubic bezier absolute
          final x1 = double.parse(commands[i++]);
          final y1 = double.parse(commands[i++]);
          final x2 = double.parse(commands[i++]);
          final y2 = double.parse(commands[i++]);
          currentX = double.parse(commands[i++]);
          currentY = double.parse(commands[i++]);
          path.cubicTo(x1, y1, x2, y2, currentX, currentY);
          lastControlX = x2;
          lastControlY = y2;
          lastCommand = 'C';
          break;
          
        case 'c': // Cubic bezier relative
          final x1 = currentX + double.parse(commands[i++]);
          final y1 = currentY + double.parse(commands[i++]);
          final x2 = currentX + double.parse(commands[i++]);
          final y2 = currentY + double.parse(commands[i++]);
          currentX += double.parse(commands[i++]);
          currentY += double.parse(commands[i++]);
          path.cubicTo(x1, y1, x2, y2, currentX, currentY);
          lastControlX = x2;
          lastControlY = y2;
          lastCommand = 'c';
          break;
          
        case 'S': // Smooth cubic bezier absolute
          double x1 = currentX * 2 - lastControlX;
          double y1 = currentY * 2 - lastControlY;
          final x2 = double.parse(commands[i++]);
          final y2 = double.parse(commands[i++]);
          currentX = double.parse(commands[i++]);
          currentY = double.parse(commands[i++]);
          path.cubicTo(x1, y1, x2, y2, currentX, currentY);
          lastControlX = x2;
          lastControlY = y2;
          lastCommand = 'S';
          break;
          
        case 's': // Smooth cubic bezier relative
          double x1 = currentX * 2 - lastControlX;
          double y1 = currentY * 2 - lastControlY;
          final x2 = currentX + double.parse(commands[i++]);
          final y2 = currentY + double.parse(commands[i++]);
          currentX += double.parse(commands[i++]);
          currentY += double.parse(commands[i++]);
          path.cubicTo(x1, y1, x2, y2, currentX, currentY);
          lastControlX = x2;
          lastControlY = y2;
          lastCommand = 's';
          break;
          
        case 'Q': // Quadratic bezier absolute
          final x1 = double.parse(commands[i++]);
          final y1 = double.parse(commands[i++]);
          currentX = double.parse(commands[i++]);
          currentY = double.parse(commands[i++]);
          path.quadraticBezierTo(x1, y1, currentX, currentY);
          lastControlX = x1;
          lastControlY = y1;
          lastCommand = 'Q';
          break;
          
        case 'q': // Quadratic bezier relative
          final x1 = currentX + double.parse(commands[i++]);
          final y1 = currentY + double.parse(commands[i++]);
          currentX += double.parse(commands[i++]);
          currentY += double.parse(commands[i++]);
          path.quadraticBezierTo(x1, y1, currentX, currentY);
          lastControlX = x1;
          lastControlY = y1;
          lastCommand = 'q';
          break;
          
        case 'T': // Smooth quadratic absolute
          lastControlX = currentX * 2 - lastControlX;
          lastControlY = currentY * 2 - lastControlY;
          currentX = double.parse(commands[i++]);
          currentY = double.parse(commands[i++]);
          path.quadraticBezierTo(lastControlX, lastControlY, currentX, currentY);
          lastCommand = 'T';
          break;
          
        case 't': // Smooth quadratic relative
          lastControlX = currentX * 2 - lastControlX;
          lastControlY = currentY * 2 - lastControlY;
          currentX += double.parse(commands[i++]);
          currentY += double.parse(commands[i++]);
          path.quadraticBezierTo(lastControlX, lastControlY, currentX, currentY);
          lastCommand = 't';
          break;
          
        case 'A': // Arc absolute
        case 'a': // Arc relative
          // Simplified - skip arc params and draw line
          // ignore: unused_local_variable
          final rx = double.parse(commands[i++]);
          // ignore: unused_local_variable
          final ry = double.parse(commands[i++]);
          // ignore: unused_local_variable
          final xAxisRotation = double.parse(commands[i++]);
          // ignore: unused_local_variable
          final largeArc = double.parse(commands[i++]);
          // ignore: unused_local_variable
          final sweep = double.parse(commands[i++]);
          if (cmd == 'A') {
            currentX = double.parse(commands[i++]);
            currentY = double.parse(commands[i++]);
          } else {
            currentX += double.parse(commands[i++]);
            currentY += double.parse(commands[i++]);
          }
          // Approximate arc with line (simplified)
          path.lineTo(currentX, currentY);
          lastCommand = cmd;
          break;
          
        case 'Z':
        case 'z': // Close path
          path.close();
          currentX = startX;
          currentY = startY;
          lastCommand = 'Z';
          break;
          
        default:
          // Unknown command, skip
          break;
      }
    }
    
    return path;
  }
  
  /// Tokenize SVG path data into commands and numbers
  static List<String> _tokenize(String pathData) {
    final tokens = <String>[];
    final regex = RegExp(r'([MmLlHhVvCcSsQqTtAaZz])|(-?[\d.]+(?:[eE][+-]?\d+)?)');
    
    for (final match in regex.allMatches(pathData)) {
      final token = match.group(0)!;
      tokens.add(token);
    }
    
    return tokens;
  }
  
  static bool _isNumber(String s) {
    return double.tryParse(s) != null;
  }
}
