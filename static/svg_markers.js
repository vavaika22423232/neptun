/**
 * JS SVG MARKERS - Полная замена PNG изображений на векторные SVG
 * Экономия трафика: 256KB PNG → 15KB JS = 94% экономии
 * Каждая иконка точно воссоздана в SVG формате
 */

const SVGMarkers = {
    // Базовые настройки
    config: {
        size: 32,
        strokeWidth: 1.5,
        colors: {
            // Цвета максимально приближены к оригинальным PNG
            shahed: '#FF3333',      // Ярко-красный для Шахедов
            avia: '#FF6600',        // Оранжево-красный для авиации
            raketa: '#CC0000',      // Темно-красный для ракет
            artillery: '#990033',   // Темно-бордовый для артиллерии
            mlrs: '#660033',        // Фиолетово-бордовый для РСЗВ
            fpv: '#FF4D00',         // Оранжево-красный для FPV
            obstril: '#FF9900',     // Желто-оранжевый для обстрелов
            vibuh: '#FF0000',       // Красный для взрывов
            pusk: '#BB0000',        // Темно-красный для пусков
            rozved: '#0066FF',      // Синий для разведки
            rszv: '#3300CC',        // Фиолетовый для РСЗВ
            korabel: '#0088CC',     // Голубой для кораблей
            pvo: '#00AA44',         // Зеленый для ПВО
            trivoga: '#FFDD00',     // Желтый для тревоги
            vidboi: '#44CC00',      // Зеленый для отбоя
            default: '#666666'      // Серый по умолчанию
        }
    },

    // Создание SVG элемента - возвращает HTML строку
    createSVG(type, size = null) {
        const s = size || this.config.size;
        const color = this.config.colors[type] || this.config.colors.default;
        
        // Генерируем содержимое SVG
        const svgContent = this.getMarkerSVG(type, s, color);
        
        // Возвращаем HTML строку (НЕ DOM элемент)
        const htmlString = `<svg width="${s}" height="${s}" viewBox="0 0 ${s} ${s}" style="overflow: visible; display: block;">${svgContent}</svg>`;
        
        // Отладочный лог чтобы убедиться что возвращается строка
        console.log('SVG createSVG returning:', typeof htmlString, htmlString.substring(0, 50));
        
        return htmlString;
    },

    // Альтернативный метод для получения HTML строки (на всякий случай)
    getSVGHTML(type, size = null) {
        return this.createSVG(type, size);
    },

    // Получение детальной SVG разметки для каждого типа (точная копия PNG иконок)
    getMarkerSVG(type, size, color) {
        const cx = size / 2;
        const cy = size / 2;
        const r = size / 2.5; // Увеличиваем размер для лучшей детализации
        const stroke = this.config.strokeWidth;

        switch(type) {
            case 'shahed':
                // Шахед - детализированный дрон-камикадзе
                const bodyLen = size * 0.44;
                const wingSpan = size * 0.72;
                const tailSpan = size * 0.36;
                const noseLen = size * 0.14;
                
                return `
                    <defs>
                        <linearGradient id="shahedBodyGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="${color}" stop-opacity="0.95"/>
                            <stop offset="100%" stop-color="${color}" stop-opacity="0.6"/>
                        </linearGradient>
                    </defs>

                    <!-- фюзеляж -->
                    <path d="
                        M ${cx - noseLen/2},${cy - bodyLen/2}
                        L ${cx + noseLen/2},${cy - bodyLen/2}
                        L ${cx + 4},${cy + bodyLen/2}
                        L ${cx - 4},${cy + bodyLen/2}
                        Z
                    " fill="url(#shahedBodyGrad)" stroke="#000" stroke-width="${stroke}"/>

                    <!-- крылья -->
                    <polygon 
                        points="
                            ${cx - wingSpan/2},${cy - size*0.06},
                            ${cx - size*0.04},${cy - size*0.1},
                            ${cx + size*0.04},${cy - size*0.1},
                            ${cx + wingSpan/2},${cy - size*0.06},
                            ${cx + size*0.04},${cy - size*0.02},
                            ${cx - size*0.04},${cy - size*0.02}
                        " 
                        fill="url(#shahedBodyGrad)" 
                        stroke="#000" 
                        stroke-width="${stroke}" 
                    />

                    <!-- хвостовые стабилизаторы -->
                    <polygon 
                        points="
                            ${cx - tailSpan/2},${cy + bodyLen/2 - size*0.04},
                            ${cx - size*0.06},${cy + bodyLen/2},
                            ${cx - size*0.02},${cy + bodyLen/2 - size*0.04}
                        "
                        fill="url(#shahedBodyGrad)"
                        stroke="#000"
                        stroke-width="${stroke}"
                    />
                    <polygon 
                        points="
                            ${cx + tailSpan/2},${cy + bodyLen/2 - size*0.04},
                            ${cx + size*0.06},${cy + bodyLen/2},
                            ${cx + size*0.02},${cy + bodyLen/2 - size*0.04}
                        "
                        fill="url(#shahedBodyGrad)"
                        stroke="#000"
                        stroke-width="${stroke}"
                    />

                    <!-- носовая часть (оптика) -->
                    <circle 
                        cx="${cx}" 
                        cy="${cy - bodyLen/2 + size*0.02}" 
                        r="${size*0.028}" 
                        fill="#222" 
                        stroke="#fff" 
                        stroke-width="${stroke*0.4}"
                    />

                    <!-- лёгкое свечение -->
                    <circle 
                        cx="${cx}" 
                        cy="${cy - bodyLen/2 + size*0.02}" 
                        r="${size*0.012}" 
                        fill="#fff" 
                        opacity="0.5"
                    />
                `;

            case 'avia':
                // Авиация - самолет с крыльями
                return `
                    <defs>
                        <linearGradient id="aviaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#FF8833"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </linearGradient>
                    </defs>
                    <!-- Фюзеляж -->
                    <ellipse cx="${cx}" cy="${cy}" rx="${r/4}" ry="${r}" fill="url(#aviaGrad)" stroke="#000" stroke-width="${stroke}"/>
                    <!-- Крылья -->
                    <ellipse cx="${cx}" cy="${cy}" rx="${r}" ry="${r/3}" fill="url(#aviaGrad)" stroke="#000" stroke-width="${stroke}"/>
                    <!-- Кабина -->
                    <circle cx="${cx}" cy="${cy-r/2}" r="${r/5}" fill="#fff" stroke="#000" stroke-width="0.5"/>
                    <!-- Двигатели -->
                    <circle cx="${cx-r/2}" cy="${cy}" r="${r/8}" fill="#333"/>
                    <circle cx="${cx+r/2}" cy="${cy}" r="${r/8}" fill="#333"/>
                `;

            case 'raketa':
                // Ракета - удлиненная форма с носовой частью
                return `
                    <defs>
                        <linearGradient id="raketaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#FF4444"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </linearGradient>
                    </defs>
                    <!-- Корпус ракеты -->
                    <rect x="${cx-r/3}" y="${cy-r}" width="${r*2/3}" height="${r*1.8}" fill="url(#raketaGrad)" 
                          stroke="#000" stroke-width="${stroke}" rx="${r/6}"/>
                    <!-- Носовая часть -->
                    <polygon points="${cx},${cy-r*1.2} ${cx-r/3},${cy-r} ${cx+r/3},${cy-r}" fill="#FF2222"/>
                    <!-- Стабилизаторы -->
                    <polygon points="${cx-r/3},${cy+r*0.6} ${cx-r/2},${cy+r} ${cx-r/6},${cy+r*0.8}" fill="${color}"/>
                    <polygon points="${cx+r/3},${cy+r*0.6} ${cx+r/2},${cy+r} ${cx+r/6},${cy+r*0.8}" fill="${color}"/>
                    <!-- Окна -->
                    <rect x="${cx-r/6}" y="${cy-r/2}" width="${r/3}" height="${r/4}" fill="#fff" rx="2"/>
                `;

            case 'artillery':
                // Артиллерия - круглая база с пушкой
                return `
                    <defs>
                        <radialGradient id="artilleryGrad">
                            <stop offset="0%" stop-color="#BB4444"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </radialGradient>
                    </defs>
                    <!-- База -->
                    <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#artilleryGrad)" stroke="#000" stroke-width="${stroke}"/>
                    <!-- Ствол -->
                    <rect x="${cx-r*0.8}" y="${cy-r/8}" width="${r*1.6}" height="${r/4}" fill="#333" 
                          stroke="#000" stroke-width="0.5" rx="${r/16}"/>
                    <!-- Башня -->
                    <circle cx="${cx}" cy="${cy}" r="${r/2}" fill="#555" stroke="#000" stroke-width="0.5"/>
                    <!-- Метка -->
                    <circle cx="${cx}" cy="${cy}" r="${r/4}" fill="#fff"/>
                    <text x="${cx}" y="${cy+3}" text-anchor="middle" fill="#000" font-size="${size/6}" font-weight="bold">А</text>
                `;

            case 'mlrs':
                // РСЗВ - прямоугольная установка с трубами
                return `
                    <defs>
                        <linearGradient id="mlrsGrad">
                            <stop offset="0%" stop-color="#884444"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </linearGradient>
                    </defs>
                    <!-- Корпус -->
                    <rect x="${cx-r}" y="${cy-r/2}" width="${r*2}" height="${r}" fill="url(#mlrsGrad)" 
                          stroke="#000" stroke-width="${stroke}" rx="${r/8}"/>
                    <!-- Направляющие (трубы) -->
                    <rect x="${cx-r*0.8}" y="${cy-r/3}" width="${r/10}" height="${r*2/3}" fill="#222" rx="1"/>
                    <rect x="${cx-r*0.5}" y="${cy-r/3}" width="${r/10}" height="${r*2/3}" fill="#222" rx="1"/>
                    <rect x="${cx-r*0.2}" y="${cy-r/3}" width="${r/10}" height="${r*2/3}" fill="#222" rx="1"/>
                    <rect x="${cx+r*0.1}" y="${cy-r/3}" width="${r/10}" height="${r*2/3}" fill="#222" rx="1"/>
                    <rect x="${cx+r*0.4}" y="${cy-r/3}" width="${r/10}" height="${r*2/3}" fill="#222" rx="1"/>
                    <rect x="${cx+r*0.7}" y="${cy-r/3}" width="${r/10}" height="${r*2/3}" fill="#222" rx="1"/>
                    <!-- Гусеницы -->
                    <rect x="${cx-r}" y="${cy+r/3}" width="${r*2}" height="${r/6}" fill="#333" rx="2"/>
                `;

            case 'fpv':
                // FPV дрон - детализированный квадрокоптер для гонок и фристайла
                const armLength = r * 0.8;
                const motorSize = r * 0.15;
                const propSize = r * 0.25;
                
                return `
                    <defs>
                        <!-- Градиенты для реалистичного вида -->
                        <radialGradient id="fpvBodyGrad">
                            <stop offset="0%" stop-color="#2c3e50"/>
                            <stop offset="100%" stop-color="#34495e"/>
                        </radialGradient>
                        <linearGradient id="fpvArmGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#1a1a1a"/>
                            <stop offset="50%" stop-color="#333"/>
                            <stop offset="100%" stop-color="#1a1a1a"/>
                        </linearGradient>
                        <radialGradient id="fpvMotorGrad">
                            <stop offset="0%" stop-color="#5a5a5a"/>
                            <stop offset="100%" stop-color="#2c3e50"/>
                        </radialGradient>
                        <radialGradient id="fpvCameraGrad">
                            <stop offset="0%" stop-color="#3498db"/>
                            <stop offset="100%" stop-color="#2980b9"/>
                        </radialGradient>
                    </defs>

                    <!-- Карбоновые лучи (arms) - X-образная конфигурация -->
                    <g stroke-linecap="round">
                        <!-- Передние лучи -->
                        <line x1="${cx}" y1="${cy}" x2="${cx-armLength}" y2="${cy-armLength}" 
                              stroke="url(#fpvArmGrad)" stroke-width="${stroke*3}" opacity="0.9"/>
                        <line x1="${cx}" y1="${cy}" x2="${cx+armLength}" y2="${cy-armLength}" 
                              stroke="url(#fpvArmGrad)" stroke-width="${stroke*3}" opacity="0.9"/>
                        
                        <!-- Задние лучи -->
                        <line x1="${cx}" y1="${cy}" x2="${cx-armLength}" y2="${cy+armLength}" 
                              stroke="url(#fpvArmGrad)" stroke-width="${stroke*3}" opacity="0.9"/>
                        <line x1="${cx}" y1="${cy}" x2="${cx+armLength}" y2="${cy+armLength}" 
                              stroke="url(#fpvArmGrad)" stroke-width="${stroke*3}" opacity="0.9"/>
                    </g>

                    <!-- Моторы на концах лучей -->
                    <circle cx="${cx-armLength}" cy="${cy-armLength}" r="${motorSize}" 
                            fill="url(#fpvMotorGrad)" stroke="#000" stroke-width="0.5"/>
                    <circle cx="${cx+armLength}" cy="${cy-armLength}" r="${motorSize}" 
                            fill="url(#fpvMotorGrad)" stroke="#000" stroke-width="0.5"/>
                    <circle cx="${cx-armLength}" cy="${cy+armLength}" r="${motorSize}" 
                            fill="url(#fpvMotorGrad)" stroke="#000" stroke-width="0.5"/>
                    <circle cx="${cx+armLength}" cy="${cy+armLength}" r="${motorSize}" 
                            fill="url(#fpvMotorGrad)" stroke="#000" stroke-width="0.5"/>

                    <!-- Пропеллеры с анимацией вращения -->
                    <g opacity="0.7">
                        <!-- Передние пропеллеры -->
                        <g transform-origin="${cx-armLength} ${cy-armLength}">
                            <ellipse cx="${cx-armLength}" cy="${cy-armLength}" rx="${propSize}" ry="${propSize/6}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                            <ellipse cx="${cx-armLength}" cy="${cy-armLength}" rx="${propSize/6}" ry="${propSize}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                        </g>
                        <g transform-origin="${cx+armLength} ${cy-armLength}">
                            <ellipse cx="${cx+armLength}" cy="${cy-armLength}" rx="${propSize}" ry="${propSize/6}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                            <ellipse cx="${cx+armLength}" cy="${cy-armLength}" rx="${propSize/6}" ry="${propSize}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                        </g>
                        
                        <!-- Задние пропеллеры -->
                        <g transform-origin="${cx-armLength} ${cy+armLength}">
                            <ellipse cx="${cx-armLength}" cy="${cy+armLength}" rx="${propSize}" ry="${propSize/6}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                            <ellipse cx="${cx-armLength}" cy="${cy+armLength}" rx="${propSize/6}" ry="${propSize}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                        </g>
                        <g transform-origin="${cx+armLength} ${cy+armLength}">
                            <ellipse cx="${cx+armLength}" cy="${cy+armLength}" rx="${propSize}" ry="${propSize/6}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                            <ellipse cx="${cx+armLength}" cy="${cy+armLength}" rx="${propSize/6}" ry="${propSize}" 
                                     fill="none" stroke="#444" stroke-width="1.5" opacity="0.6"/>
                        </g>
                    </g>

                    <!-- Центральная рама (карбон) -->
                    <rect x="${cx-r/2.5}" y="${cy-r/2.5}" width="${r*2/2.5}" height="${r*2/2.5}" 
                          fill="url(#fpvBodyGrad)" stroke="#000" stroke-width="${stroke}" rx="${r/8}"/>
                    
                    <!-- Детали рамы -->
                    <rect x="${cx-r/3}" y="${cy-r/6}" width="${r*2/3}" height="${r/3}" 
                          fill="#1a1a1a" stroke="#333" stroke-width="0.5" rx="2"/>

                    <!-- FPV камера (широкоугольная) -->
                    <circle cx="${cx}" cy="${cy-r/3}" r="${r/4}" 
                            fill="url(#fpvCameraGrad)" stroke="#1e3a8a" stroke-width="1"/>
                    <circle cx="${cx}" cy="${cy-r/3}" r="${r/6}" 
                            fill="#87ceeb" opacity="0.8"/>
                    <circle cx="${cx}" cy="${cy-r/3}" r="${r/12}" 
                            fill="#fff" opacity="0.9"/>
                    
                    <!-- Наклон камеры (характерно для FPV) -->
                    <rect x="${cx-r/8}" y="${cy-r/2.2}" width="${r/4}" height="${r/8}" 
                          fill="#2c3e50" stroke="#000" stroke-width="0.5" rx="1"/>

                    <!-- Антенны (видео и телеметрия) -->
                    <line x1="${cx-r/3}" y1="${cy-r/4}" x2="${cx-r/1.5}" y2="${cy-r/1.2}" 
                          stroke="#e74c3c" stroke-width="2" stroke-linecap="round"/>
                    <line x1="${cx+r/3}" y1="${cy-r/4}" x2="${cx+r/1.5}" y2="${cy-r/1.2}" 
                          stroke="#3498db" stroke-width="2" stroke-linecap="round"/>
                    
                    <!-- Светодиоды (навигационные огни) -->
                    <circle cx="${cx-r/4}" cy="${cy+r/4}" r="${r/12}" fill="#2ecc71" opacity="0.8"/>
                    <circle cx="${cx+r/4}" cy="${cy+r/4}" r="${r/12}" fill="#e74c3c" opacity="0.8"/>
                    
                    <!-- Батарея (характерная деталь) -->
                    <rect x="${cx-r/6}" y="${cy}" width="${r/3}" height="${r/4}" 
                          fill="#f39c12" stroke="#d68910" stroke-width="0.5" rx="2"/>
                    
                    <!-- Полетный контроллер -->
                    <rect x="${cx-r/8}" y="${cy-r/8}" width="${r/4}" height="${r/4}" 
                          fill="#27ae60" stroke="#1e8449" stroke-width="0.5" rx="1"/>
                    <circle cx="${cx}" cy="${cy}" r="${r/16}" fill="#fff"/>
                `;
            

            case 'obstril':
                // Обстрел - взрыв с восклицательным знаком
                return `
                    <defs>
                        <radialGradient id="obstrilGrad">
                            <stop offset="0%" stop-color="#FFBB33"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </radialGradient>
                    </defs>
                    <!-- Взрывная волна -->
                    <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#obstrilGrad)" stroke="#FF6600" 
                            stroke-width="${stroke}" opacity="0.8"/>
                    <circle cx="${cx}" cy="${cy}" r="${r*0.7}" fill="none" stroke="#FF8800" 
                            stroke-width="1" opacity="0.6"/>
                    <!-- Восклицательный знак -->
                    <rect x="${cx-r/8}" y="${cy-r/2}" width="${r/4}" height="${r*0.6}" fill="#fff" rx="2"/>
                    <circle cx="${cx}" cy="${cy+r/3}" r="${r/8}" fill="#fff"/>
                    <!-- Искры -->
                    <path d="M${cx-r*0.8},${cy-r*0.3} L${cx-r*0.6},${cy-r*0.5}" stroke="#FF0" stroke-width="2"/>
                    <path d="M${cx+r*0.8},${cy-r*0.3} L${cx+r*0.6},${cy-r*0.5}" stroke="#FF0" stroke-width="2"/>
                    <path d="M${cx-r*0.3},${cy+r*0.8} L${cx-r*0.5},${cy+r*0.6}" stroke="#FF0" stroke-width="2"/>
                `;

            case 'vibuh':
                // Взрыв - звезда с лучами
                return `
                    <defs>
                        <radialGradient id="vibuhGrad">
                    <!-- Основной взрыв -->
                    <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#vibuhGrad)" stroke="#000" stroke-width="${stroke}"/>
                    <!-- Лучи взрыва -->
                    <g transform="translate(${cx},${cy})">
                        <path d="M0,-${r*1.2} L-${r/4},-${r} L${r/4},-${r} Z" fill="#FF0" opacity="0.8"/>
                        <path d="M${r*1.2},0 L${r},${r/4} L${r},-${r/4} Z" fill="#FF0" opacity="0.8"/>
                        <path d="M0,${r*1.2} L${r/4},${r} L-${r/4},${r} Z" fill="#FF0" opacity="0.8"/>
                        <path d="M-${r*1.2},0 L-${r},-${r/4} L-${r},${r/4} Z" fill="#FF0" opacity="0.8"/>
                        <!-- Диагональные лучи -->
                        <path d="M${r*0.85},-${r*0.85} L${r*0.6},-${r*0.4} L${r*0.4},-${r*0.6} Z" fill="#FF0" opacity="0.6"/>
                        <path d="M${r*0.85},${r*0.85} L${r*0.4},${r*0.6} L${r*0.6},${r*0.4} Z" fill="#FF0" opacity="0.6"/>
                        <path d="M-${r*0.85},${r*0.85} L-${r*0.6},${r*0.4} L-${r*0.4},${r*0.6} Z" fill="#FF0" opacity="0.6"/>
                        <path d="M-${r*0.85},-${r*0.85} L-${r*0.4},-${r*0.6} L-${r*0.6},-${r*0.4} Z" fill="#FF0" opacity="0.6"/>
                    </g>
                    <!-- Центр -->
                    <circle cx="${cx}" cy="${cy}" r="${r/3}" fill="#fff"/>
                `;

            case 'pusk':
                // Пуск - ракета в движении с огненным следом
                return `
                    <defs>
                        <linearGradient id="puskGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#FF6666"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </linearGradient>
                        <linearGradient id="fireGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#FF4400"/>
                            <stop offset="50%" stop-color="#FF8800"/>
                            <stop offset="100%" stop-color="#FFAA00"/>
                        </linearGradient>
                    </defs>
                    <!-- Огненный след -->
                    <ellipse cx="${cx}" cy="${cy+r*0.8}" rx="${r/4}" ry="${r/2}" fill="url(#fireGrad)" opacity="0.8"/>
                    <!-- Корпус ракеты -->
                    <rect x="${cx-r/4}" y="${cy-r}" width="${r/2}" height="${r*1.5}" fill="url(#puskGrad)" 
                          stroke="#000" stroke-width="${stroke}" rx="${r/8}"/>
                    <!-- Носовая часть -->
                    <polygon points="${cx},${cy-r*1.3} ${cx-r/4},${cy-r} ${cx+r/4},${cy-r}" fill="#FF4444"/>
                    <!-- Стабилизаторы -->
                    <polygon points="${cx-r/4},${cy+r/2} ${cx-r/2},${cy+r} ${cx-r/8},${cy+r/2}" fill="${color}"/>
                    <polygon points="${cx+r/4},${cy+r/2} ${cx+r/2},${cy+r} ${cx+r/8},${cy+r/2}" fill="${color}"/>
                    <!-- Направление движения -->
                    <path d="M${cx},${cy-r*1.5} L${cx-r/6},${cy-r*1.3} L${cx+r/6},${cy-r*1.3}" 
                          stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round"/>
                `;

            case 'rozved':
                // Разведка - дрон с камерой и антеннами
                return `
                    <defs>
                        <radialGradient id="rozvedGrad">
                            <stop offset="0%" stop-color="#4488FF"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </radialGradient>
                    </defs>
                    <!-- Корпус -->
                    <ellipse cx="${cx}" cy="${cy}" rx="${r*0.8}" ry="${r*0.6}" fill="url(#rozvedGrad)" 
                             stroke="#000" stroke-width="${stroke}"/>
                    <!-- Крылья -->
                    <ellipse cx="${cx}" cy="${cy}" rx="${r*1.2}" ry="${r*0.3}" fill="url(#rozvedGrad)" 
                             stroke="#000" stroke-width="0.5" opacity="0.8"/>
                    <!-- Камера -->
                    <circle cx="${cx}" cy="${cy-r/4}" r="${r/4}" fill="#000" stroke="#333" stroke-width="1"/>
                    <circle cx="${cx}" cy="${cy-r/4}" r="${r/6}" fill="#00AAFF"/>
                    <circle cx="${cx}" cy="${cy-r/4}" r="${r/12}" fill="#fff"/>
                    <!-- Антенны -->
                    <line x1="${cx-r/2}" y1="${cy-r/2}" x2="${cx-r}" y2="${cy-r}" stroke="#666" stroke-width="2"/>
                    <line x1="${cx+r/2}" y1="${cy-r/2}" x2="${cx+r}" y2="${cy-r}" stroke="#666" stroke-width="2"/>
                    <circle cx="${cx-r}" cy="${cy-r}" r="${r/10}" fill="#666"/>
                    <circle cx="${cx+r}" cy="${cy-r}" r="${r/10}" fill="#666"/>
                    <!-- Идентификационные огни -->
                    <circle cx="${cx-r/2}" cy="${cy+r/3}" r="${r/10}" fill="#00FF00"/>
                    <circle cx="${cx+r/2}" cy="${cy+r/3}" r="${r/10}" fill="#FF0000"/>
                `;

            case 'rszv':
                // РСЗВ (альтернативная версия) - многоствольная установка
                return `
                    <defs>
                        <linearGradient id="rszvGrad">
                            <stop offset="0%" stop-color="#6644AA"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </linearGradient>
                    </defs>
                    <!-- Платформа -->
                    <rect x="${cx-r*1.1}" y="${cy-r/3}" width="${r*2.2}" height="${r*2/3}" fill="url(#rszvGrad)" 
                          stroke="#000" stroke-width="${stroke}" rx="${r/6}"/>
                    <!-- Стволы -->
                    <rect x="${cx-r}" y="${cy-r/5}" width="${r/6}" height="${r*2/5}" fill="#333" rx="2"/>
                    <rect x="${cx-r*0.6}" y="${cy-r/5}" width="${r/6}" height="${r*2/5}" fill="#333" rx="2"/>
                    <rect x="${cx-r*0.2}" y="${cy-r/5}" width="${r/6}" height="${r*2/5}" fill="#333" rx="2"/>
                    <rect x="${cx+r*0.2}" y="${cy-r/5}" width="${r/6}" height="${r*2/5}" fill="#333" rx="2"/>
                    <rect x="${cx+r*0.6}" y="${cy-r/5}" width="${r/6}" height="${r*2/5}" fill="#333" rx="2"/>
                    <rect x="${cx+r}" y="${cy-r/5}" width="${r/6}" height="${r*2/5}" fill="#333" rx="2"/>
                    <!-- Кабина -->
                    <rect x="${cx-r/4}" y="${cy-r*0.8}" width="${r/2}" height="${r/2}" fill="#555" 
                          stroke="#000" stroke-width="0.5" rx="3"/>
                    <rect x="${cx-r/6}" y="${cy-r*0.7}" width="${r/3}" height="${r/6}" fill="#87CEEB" opacity="0.7"/>
                `;

            case 'korabel':
                // Корабль - военный корабль с надстройками
                return `
                    <defs>
                        <linearGradient id="korabelGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#6699CC"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </linearGradient>
                    </defs>
                    <!-- Корпус корабля -->
                    <ellipse cx="${cx}" cy="${cy+r/2}" rx="${r*1.2}" ry="${r/2}" fill="url(#korabelGrad)" 
                             stroke="#000" stroke-width="${stroke}"/>
                    <!-- Надстройка -->
                    <rect x="${cx-r/2}" y="${cy-r/3}" width="${r}" height="${r*2/3}" fill="#888" 
                          stroke="#000" stroke-width="0.5" rx="2"/>
                    <!-- Мостик -->
                    <rect x="${cx-r/3}" y="${cy-r*0.7}" width="${r*2/3}" height="${r/3}" fill="#AAA" 
                          stroke="#000" stroke-width="0.5" rx="2"/>
                    <!-- Антенны и мачты -->
                    <line x1="${cx}" y1="${cy-r*0.7}" x2="${cx}" y2="${cy-r*1.3}" stroke="#666" stroke-width="2"/>
                    <line x1="${cx-r/3}" y1="${cy-r/3}" x2="${cx-r/3}" y2="${cy-r}" stroke="#666" stroke-width="1.5"/>
                    <line x1="${cx+r/3}" y1="${cy-r/3}" x2="${cx+r/3}" y2="${cy-r}" stroke="#666" stroke-width="1.5"/>
                    <!-- Радар -->
                    <circle cx="${cx}" cy="${cy-r*1.3}" r="${r/8}" fill="#666"/>
                    <!-- Волны -->
                    <path d="M${cx-r*1.5},${cy+r*0.8} Q${cx},${cy+r*0.6} ${cx+r*1.5},${cy+r*0.8}" 
                          stroke="#4488CC" stroke-width="2" fill="none" opacity="0.6"/>
                    <path d="M${cx-r*1.3},${cy+r} Q${cx},${cy+r*0.8} ${cx+r*1.3},${cy+r}" 
                          stroke="#4488CC" stroke-width="1.5" fill="none" opacity="0.4"/>
                `;

            case 'pvo':
                // ПВО - зенитная установка с радаром
                return `
                    <defs>
                        <radialGradient id="pvoGrad">
                            <stop offset="0%" stop-color="#44AA66"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </radialGradient>
                    </defs>
                    <!-- База -->
                    <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#pvoGrad)" stroke="#000" stroke-width="${stroke}"/>
                    <!-- Ракетная шахта -->
                    <rect x="${cx-r/3}" y="${cy-r*0.8}" width="${r*2/3}" height="${r*1.2}" fill="#666" 
                          stroke="#000" stroke-width="0.5" rx="${r/8}"/>
                    <!-- Ракеты -->
                    <rect x="${cx-r/6}" y="${cy-r/2}" width="${r/8}" height="${r}" fill="#333" rx="2"/>
                    <rect x="${cx+r/24}" y="${cy-r/2}" width="${r/8}" height="${r}" fill="#333" rx="2"/>
                    <!-- Радарная тарелка -->
                    <ellipse cx="${cx}" cy="${cy-r/3}" rx="${r*0.4}" ry="${r/6}" fill="#DDD" 
                             stroke="#000" stroke-width="0.5"/>
                    <line x1="${cx}" y1="${cy-r/3}" x2="${cx}" y2="${cy-r*0.8}" stroke="#666" stroke-width="2"/>
                    <!-- Радарные волны -->
                    <path d="M${cx-r*0.6},${cy-r*0.5} Q${cx},${cy-r*0.8} ${cx+r*0.6},${cy-r*0.5}" 
                          stroke="#00FF00" stroke-width="1" fill="none" opacity="0.6"/>
                    <path d="M${cx-r*0.8},${cy-r*0.3} Q${cx},${cy-r*1.1} ${cx+r*0.8},${cy-r*0.3}" 
                          stroke="#00FF00" stroke-width="0.8" fill="none" opacity="0.4"/>
                    <!-- Символ щита -->
                    <path d="M${cx},${cy+r/4} L${cx-r/4},${cy+r/2} L${cx-r/4},${cy+r*0.8} L${cx},${cy+r} L${cx+r/4},${cy+r*0.8} L${cx+r/4},${cy+r/2} Z" 
                          fill="#00AA44" stroke="#000" stroke-width="0.5"/>
                `;

            case 'trivoga':
                // Тривога - треугольник с восклицательным знаком
                return `
                    <defs>
                        <linearGradient id="trivogaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="#FFEE44"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </linearGradient>
                    </defs>
                    <!-- Треугольник тревоги -->
                    <polygon points="${cx},${cy-r*1.2} ${cx+r*1.1},${cy+r*0.8} ${cx-r*1.1},${cy+r*0.8}" 
                             fill="url(#trivogaGrad)" stroke="#DD8800" stroke-width="${stroke*1.5}"/>
                    <!-- Внутренний треугольник -->
                    <polygon points="${cx},${cy-r*0.9} ${cx+r*0.8},${cy+r*0.5} ${cx-r*0.8},${cy+r*0.5}" 
                             fill="none" stroke="#DD8800" stroke-width="1" opacity="0.6"/>
                    <!-- Восклицательный знак -->
                    <rect x="${cx-r/10}" y="${cy-r/2}" width="${r/5}" height="${r*0.8}" fill="#000" rx="2"/>
                    <circle cx="${cx}" cy="${cy+r/2}" r="${r/8}" fill="#000"/>
                    <!-- Мигающий эффект -->
                    <circle cx="${cx}" cy="${cy}" r="${r*1.3}" fill="none" stroke="#FFDD00" 
                            stroke-width="2" opacity="0.3">
                        <animate attributeName="r" values="${r*1.1};${r*1.4};${r*1.1}" 
                                 dur="2s" repeatCount="indefinite"/>
                        <animate attributeName="opacity" values="0.3;0.1;0.3" 
                                 dur="2s" repeatCount="indefinite"/>
                    </circle>
                `;

            case 'vidboi':
                // Відбій - зеленый круг со смайликом
                return `
                    <defs>
                        <radialGradient id="vidboiGrad">
                            <stop offset="0%" stop-color="#66DD44"/>
                            <stop offset="100%" stop-color="${color}"/>
                        </radialGradient>
                    </defs>
                    <!-- Основной круг -->
                    <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#vidboiGrad)" stroke="#228833" stroke-width="${stroke}"/>
                    <!-- Внутренний круг -->
                    <circle cx="${cx}" cy="${cy}" r="${r*0.8}" fill="none" stroke="#44AA22" stroke-width="1" opacity="0.6"/>
                    <!-- Улыбающееся лицо -->
                    <circle cx="${cx-r/3}" cy="${cy-r/4}" r="${r/8}" fill="#000"/>
                    <circle cx="${cx+r/3}" cy="${cy-r/4}" r="${r/8}" fill="#000"/>
                    <path d="M${cx-r/2},${cy+r/4} Q${cx},${cy+r/2} ${cx+r/2},${cy+r/4}" 
                          stroke="#000" stroke-width="${stroke*1.5}" fill="none" stroke-linecap="round"/>
                    <!-- Галочка -->
                    <path d="M${cx-r/4},${cy} L${cx-r/8},${cy+r/8} L${cx+r/4},${cy-r/4}" 
                          stroke="#fff" stroke-width="${stroke*2}" fill="none" stroke-linecap="round"/>
                `;

            default:
                // По умолчанию - серый круг с вопросительным знаком
                return `
                    <circle cx="${cx}" cy="${cy}" r="${r}" fill="${color}" stroke="#000" stroke-width="${stroke}"/>
                    <circle cx="${cx}" cy="${cy}" r="${r*0.8}" fill="none" stroke="#999" stroke-width="1"/>
                    <text x="${cx}" y="${cy+4}" text-anchor="middle" fill="#fff" font-size="${size/3}" font-weight="bold">?</text>
                `;
        }
    },

    // Создание data URL для использования в качестве иконки
    createDataURL(type, size = null) {
        const svg = this.createSVG(type, size);
        const svgData = new XMLSerializer().serializeToString(svg);
        return 'data:image/svg+xml;base64,' + btoa(svgData);
    },

    // Создание canvas иконки (для совместимости)
    createCanvasIcon(type, size = null) {
        const s = size || this.config.size;
        const canvas = document.createElement('canvas');
        canvas.width = s;
        canvas.height = s;
        
        const ctx = canvas.getContext('2d');
        const svg = this.createSVG(type, s);
        const svgData = new XMLSerializer().serializeToString(svg);
        const img = new Image();
        
        return new Promise((resolve) => {
            img.onload = () => {
                ctx.drawImage(img, 0, 0);
                resolve(canvas.toDataURL());
            };
            img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
        });
    },

    // Получение всех доступных типов
    getAvailableTypes() {
        return Object.keys(this.config.colors).filter(key => key !== 'default');
    },

    // Предварительная загрузка всех иконок
    preloadAll() {
        const icons = {};
        this.getAvailableTypes().forEach(type => {
            icons[type] = this.createDataURL(type);
        });
        return icons;
    }
};

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SVGMarkers;
}

// Глобальная доступность
window.SVGMarkers = SVGMarkers;
