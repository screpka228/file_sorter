import os
import json
import ctypes
import socket
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI()

MANIFEST_PATH = "sorting_manifest.json"

class SortAction(BaseModel):
    item_path: str
    category: str

class MediaKeyAction(BaseModel):
    action: str

def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_manifest(manifest):
    try:
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения манифеста: {e}")

def generate_report_file():
    manifest = load_manifest()
    export_path = "otchet_sortirovki.txt"
    try:
        with open(export_path, "w", encoding="utf-8") as f:
            f.write("=== ОТЧЕТ СОРТИРОВКИ ФАЙЛОВ ===\n\n")
            categories = {}
            for path, cat in manifest.items():
                categories.setdefault(cat, []).append(path)
            
            for cat, paths in categories.items():
                f.write(f"[{cat}]\n")
                filtered_paths = []
                sorted_paths = sorted(paths, key=len)
                for p in sorted_paths:
                    is_subpath = any(p.startswith(parent + os.sep) for parent in filtered_paths)
                    if not is_subpath:
                        filtered_paths.append(p)
                
                for p in filtered_paths:
                    f.write(f"  - {p}\n")
                f.write("\n")
        return os.path.abspath(export_path)
    except Exception as e:
        print(f"Ошибка генерации отчёта: {e}")
        return None

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Умный проводник-сортировщик</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        html, body {
            width: 100%;
            min-height: 100%;
            margin: 0;
            padding: 0;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
        }
        input {
            user-select: text;
            -webkit-user-select: text;
        }
    </style>
</head>
<body id="pageBody" class="bg-slate-900 text-slate-100 p-3 md:p-6 transition-colors duration-300">
    <div class="max-w-7xl mx-auto space-y-4 pb-24">
        <!-- Шапка -->
        <div class="flex flex-wrap justify-between items-center gap-3">
            <div>
                <h1 id="mainTitle" class="text-xl md:text-2xl font-bold text-cyan-400 transition-colors">Умный проводник-сортировщик</h1>
                <p id="subTitle" class="text-xs text-slate-400 mt-0.5">Раскидываем флешечный мусор без забивания диска</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
                <select id="themeSelect" onchange="changeTheme(this.value)" class="bg-slate-800 border border-slate-700 text-slate-200 text-xs md:text-sm rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500">
                    <option value="slate">🌙 Тёмный Слейт</option>
                    <option value="cyberpunk">⚡ Киберпанк</option>
                    <option value="matrix">💻 Матрица</option>
                    <option value="sunset">🌆 Закат</option>
                    <option value="monochrome">⬛ Монохром</option>
                    <option value="winter">❄️ Зимний вайб</option>
                </select>
                <button onclick="openSettings()" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition text-slate-200 shadow">
                    ⚙️ Настройки
                </button>
                <button onclick="openTextViewer()" class="bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg font-semibold transition text-xs md:text-sm shadow border border-slate-600">
                    👁️ Отчёт
                </button>
                <button onclick="saveReportToRoot()" class="bg-emerald-600 hover:bg-emerald-500 px-3 py-1.5 rounded-lg font-semibold transition text-xs md:text-sm shadow-lg">
                    💾 Сохранить в корень
                </button>
            </div>
        </div>
        
        <!-- Панель ввода пути и навигация -->
        <div id="topPanel" class="bg-slate-800/90 backdrop-blur p-3 rounded-xl flex flex-wrap gap-3 items-center shadow-lg border border-slate-700/65 transition-colors">
            <button onclick="navigateParent()" id="backBtn" class="bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg font-semibold transition text-xs md:text-sm disabled:opacity-50">📁 Наверх (Esc)</button>
            <input type="text" id="dirPath" placeholder="Введите путь (например, D:\\Flash)" 
                   class="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500 font-mono text-xs md:text-sm min-w-[200px]">
            <button onclick="loadDir()" class="bg-cyan-600 hover:bg-cyan-500 px-4 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition shadow">Открыть</button>
            <button onclick="openInExplorer()" class="bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-lg font-semibold transition text-xs md:text-sm shadow">
                📂 В проводнике
            </button>
        </div>

        <!-- Прогресс-бар -->
        <div id="progressCard" class="bg-slate-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-slate-700/65 transition-colors space-y-1.5">
            <div class="flex justify-between items-center text-xs font-semibold text-slate-300">
                <span>📊 Прогресс сортировки:</span>
                <span id="progressText">0%</span>
            </div>
            <div class="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-700/50">
                <div id="progressBar" class="bg-cyan-500 h-full transition-all duration-300 w-0"></div>
            </div>
        </div>

        <!-- Основной контент: Категории и Списки -->
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4 items-start">
            <!-- Панель категорий -->
            <div id="catPanel" class="bg-slate-800/90 backdrop-blur p-3 rounded-xl space-y-1 shadow-lg border border-slate-700/65 transition-colors">
                <h2 id="catTitle" class="font-bold text-base text-slate-300 mb-1.5">Категории</h2>
                <div id="categories" class="space-y-1">
                    <button data-cat="Несортированные" onclick="setCategory('Несортированные')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex justify-between items-center text-xs md:text-sm border border-slate-700"><span>🔄 Несортированные</span></button>
                    <button data-cat="Игры" onclick="setCategory('Игры')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>🎮 Игры</span></button>
                    <button data-cat="Steam" onclick="setCategory('Steam')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>🕹️ Steam</span></button>
                    <button data-cat="Репаки" onclick="setCategory('Репаки')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>💿 Репаки / Установщики</span></button>
                    <button data-cat="Проекты" onclick="setCategory('Проекты')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>🛠️ Проекты</span></button>
                    <button data-cat="Софт" onclick="setCategory('Софт')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>💻 Софт / Программы</span></button>
                    <button data-cat="Прошивки" onclick="setCategory('Прошивки')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>🔌 Прошивки</span></button>
                    <button data-cat="Образы" onclick="setCategory('Образы')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>💿 Образы / ISO</span></button>
                    <button data-cat="Бэкапы" onclick="setCategory('Бэкапы')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>📦 Бэкапы</span></button>
                    <button data-cat="Музыка" onclick="setCategory('Музыка')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>🎵 Музыка</span></button>
                    <button data-cat="Видео" onclick="setCategory('Видео')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>🎬 Видео / Фильмы</span></button>
                    <button data-cat="Документы" onclick="setCategory('Документы')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>📄 Документы</span></button>
                    <button data-cat="Фото" onclick="setCategory('Фото')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 transition flex justify-between items-center text-xs md:text-sm border border-transparent"><span>📷 Фото / Картинки</span></button>
                    <button data-cat="Неизвестно" onclick="setCategory('Неизвестно')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-yellow-900/30 hover:bg-yellow-900/50 text-yellow-300 transition flex justify-between items-center text-xs md:text-sm border border-yellow-700/40"><span>❓ Неизвестно</span></button>
                    <button data-cat="Мусор" onclick="setCategory('Мусор')" class="cat-btn w-full text-left px-2.5 py-1.5 rounded bg-red-900/40 hover:bg-red-900/60 text-red-300 transition flex justify-between items-center text-xs md:text-sm border border-red-700/40"><span>🗑️ Мусор</span></button>
                </div>
                <div class="pt-2 border-t border-slate-700 mt-1.5">
                    <p class="text-[11px] text-slate-400 mb-0.5">Активная категория:</p>
                    <span id="activeCategory" class="font-bold text-cyan-400 text-sm transition-colors">Несортированные</span>
                </div>
            </div>

            <!-- Список элементов папки -->
            <div id="listPanel" class="lg:col-span-3 bg-slate-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-slate-700/65 flex flex-col h-[550px] md:h-[620px] transition-colors">
                <div class="flex justify-between items-center mb-3">
                    <h2 class="font-bold text-base text-slate-300">Элементов: <span id="itemCount">0</span></h2>
                    <span class="text-[11px] text-slate-400">ЛКМ — категория | ПКМ — выделить в проводнике | Двойной — войти | Esc — назад</span>
                </div>
                <div id="itemList" class="flex-1 overflow-y-auto space-y-1.5 pr-1">
                    <p class="text-slate-500 text-center py-20 text-sm">Введите путь и нажмите «Открыть»</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Панель мультимедиа-клавиш -->
    <div id="mediaBar" class="fixed bottom-0 left-0 right-0 bg-slate-950/95 backdrop-blur border-t border-slate-800 p-2.5 shadow-2xl z-40 transition-colors">
        <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-2">
                <span class="text-lg">⌨️</span>
                <span class="text-xs font-semibold text-slate-300">Медиа-панель:</span>
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
                <button onclick="sendMediaKey('prev')" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 px-2.5 py-1 rounded-md text-xs font-semibold text-slate-200 transition shadow">⏮ Назад</button>
                <button onclick="sendMediaKey('playpause')" class="bg-cyan-600 hover:bg-cyan-500 px-3 py-1 rounded-md text-xs font-bold text-white transition shadow">⏯ Плей/Пауза</button>
                <button onclick="sendMediaKey('next')" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 px-2.5 py-1 rounded-md text-xs font-semibold text-slate-200 transition shadow">Вперед ⏭</button>
                <div class="h-4 w-[1px] bg-slate-700 mx-1 hidden sm:block"></div>
                <button onclick="sendMediaKey('voldown')" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 px-2 py-1 rounded-md text-xs font-semibold text-slate-200 transition shadow">🔉 Тихо (-)</button>
                <button onclick="sendMediaKey('volup')" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 px-2.5 py-1 rounded-md text-xs font-semibold text-slate-200 transition shadow">🔊 Громче (+)</button>
                <button onclick="sendMediaKey('mute')" class="bg-red-900/40 hover:bg-red-900/60 border border-red-700/50 px-2 py-1 rounded-md text-xs font-semibold text-red-300 transition shadow">🔇 Mute</button>
            </div>
        </div>
    </div>

    <!-- Модальное окно просмотра отчёта -->
    <div id="textModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm hidden z-50 flex items-center justify-center p-4">
        <div class="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-3xl flex flex-col max-h-[85vh] shadow-2xl">
            <div class="flex justify-between items-center p-3 border-b border-slate-800">
                <h3 class="font-bold text-base text-slate-200">📄 Отчёт сортировки</h3>
                <button onclick="closeTextViewer()" class="text-slate-400 hover:text-slate-100 text-lg font-bold px-2">&times;</button>
            </div>
            <div class="p-3 flex-1 overflow-y-auto font-mono text-xs text-slate-300 whitespace-pre-wrap bg-slate-950/50 leading-relaxed" id="textContent">Загрузка...</div>
            <div class="p-3 border-t border-slate-800 flex justify-end gap-2">
                <button onclick="closeTextViewer()" class="bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg text-xs font-semibold transition">Закрыть</button>
            </div>
        </div>
    </div>

    <!-- Модальное окно Настройки -->
    <div id="settingsModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm hidden z-50 flex items-center justify-center p-4">
        <div class="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md flex flex-col shadow-2xl p-5 space-y-3">
            <div class="flex justify-between items-center border-b border-slate-800 pb-2.5">
                <h3 class="font-bold text-base text-slate-200">⚙️ Настройки интерфейса</h3>
                <button onclick="closeSettings()" class="text-slate-400 hover:text-slate-100 text-lg font-bold">&times;</button>
            </div>
            <div class="space-y-2.5">
                <label class="flex items-center justify-between cursor-pointer p-2 bg-slate-800/60 rounded-lg border border-slate-700/50">
                    <span class="text-xs md:text-sm text-slate-200">Показывать медиа-панель</span>
                    <input type="checkbox" id="mediaBarToggle" onchange="toggleMediaBar(this.checked)" class="w-4 h-4 accent-cyan-500 cursor-pointer">
                </label>
                <label class="flex items-center justify-between cursor-pointer p-2 bg-slate-800/60 rounded-lg border border-slate-700/50">
                    <span class="text-xs md:text-sm text-slate-200">Показывать прогресс-бар</span>
                    <input type="checkbox" id="progressBarToggle" onchange="toggleProgressBar(this.checked)" class="w-4 h-4 accent-cyan-500 cursor-pointer">
                </label>
            </div>
            <div class="flex justify-end pt-1">
                <button onclick="closeSettings()" class="bg-cyan-600 hover:bg-cyan-500 px-3.5 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition">Готово</button>
            </div>
        </div>
    </div>

    <script>
        let currentCategory = "Несортированные";
        let currentPath = "";
        let parentPath = null;
        let itemsData = [];

        window.addEventListener('DOMContentLoaded', () => {
            const mediaBarEnabled = localStorage.getItem('mediaBar') !== 'false';
            document.getElementById('mediaBarToggle').checked = mediaBarEnabled;
            applyMediaBarState(mediaBarEnabled);

            const progressEnabled = localStorage.getItem('progressBar') !== 'false';
            document.getElementById('progressBarToggle').checked = progressEnabled;
            applyProgressBarState(progressEnabled);

            const savedPath = localStorage.getItem('lastPath');
            if (savedPath) {
                document.getElementById('dirPath').value = savedPath;
                loadDir(savedPath);
            }

            updateCategoryHighlight();

            document.getElementById('dirPath').addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    loadDir();
                }
            });

            window.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    const textModal = document.getElementById('textModal');
                    const settingsModal = document.getElementById('settingsModal');
                    if (!textModal.classList.contains('hidden')) {
                        closeTextViewer();
                    } else if (!settingsModal.classList.contains('hidden')) {
                        closeSettings();
                    } else {
                        navigateParent();
                    }
                }
            });
        });

        function setCategory(cat) {
            currentCategory = cat;
            document.getElementById('activeCategory').innerText = cat;
            updateCategoryHighlight();
        }

        function updateCategoryHighlight() {
            document.querySelectorAll('.cat-btn').forEach(btn => {
                const btnCat = btn.getAttribute('data-cat');
                if (btnCat === currentCategory) {
                    btn.classList.add('ring-2', 'ring-cyan-400', 'bg-cyan-950/60', 'font-bold');
                    btn.classList.remove('border-transparent', 'border-slate-700');
                } else {
                    btn.classList.remove('ring-2', 'ring-cyan-400', 'bg-cyan-950/60', 'font-bold');
                    if (btnCat === 'Несортированные') {
                        btn.classList.add('border-slate-700');
                    } else {
                        btn.classList.add('border-transparent');
                    }
                }
            });
        }

        async function loadDir(path = null) {
            const targetPath = path || document.getElementById('dirPath').value;
            if (!targetPath) return alert('Введите путь!');
            
            try {
                const res = await fetch(`/api/browse?path=${encodeURIComponent(targetPath)}`);
                const data = await res.json();
                
                if (res.ok) {
                    currentPath = data.current_path;
                    parentPath = data.parent_path;
                    document.getElementById('dirPath').value = currentPath;
                    localStorage.setItem('lastPath', currentPath);
                    const backBtn = document.getElementById('backBtn');
                    backBtn.disabled = !parentPath;
                    itemsData = data.items;
                    renderItems();
                } else {
                    alert(data.detail || 'Ошибка загрузки папки');
                }
            } catch (err) {
                alert('Не удалось связаться с сервером');
            }
        }

        function navigateParent() {
            if (parentPath) loadDir(parentPath);
        }

        async function openInExplorer() {
            const pathOpen = document.getElementById('dirPath').value;
            if (!pathOpen) return alert('Путь не указан!');
            try {
                const res = await fetch(`/api/open-explorer?path=${encodeURIComponent(pathOpen)}`, {
                    method: 'POST'
                });
                if (!res.ok) {
                    const data = await res.json();
                    alert(data.detail || 'Ошибка открытия проводника');
                }
            } catch (err) {
                alert('Ошибка запроса к серверу');
            }
        }

        async function openItemInExplorer(itemPath, e) {
            e.stopPropagation();
            try {
                await fetch(`/api/open-explorer?path=${encodeURIComponent(itemPath)}`, {
                    method: 'POST'
                });
            } catch (err) {
                console.error('Ошибка открытия файла', err);
            }
        }

        async function sendMediaKey(action) {
            try {
                await fetch('/api/media-key', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: action})
                });
            } catch (err) {
                console.error('Ошибка медиа-клавиши', err);
            }
        }

        async function saveReportToRoot() {
            try {
                const res = await fetch('/api/save-report', { method: 'POST' });
                const data = await res.json();
                if (res.ok) {
                    alert(`✅ Отчёт успешно сохранён в корень проекта:\\n${data.path}`);
                } else {
                    alert(data.detail || 'Ошибка сохранения отчёта');
                }
            } catch (err) {
                alert('Не удалось сохранить отчёт');
            }
        }

        async function assignCategory(itemPath) {
            const res = await fetch('/api/sort', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({item_path: itemPath, category: currentCategory})
            });
            
            if (res.ok) {
                const data = await res.json();
                if (data.updated_paths) {
                    data.updated_paths.forEach(p => {
                        const item = itemsData.find(i => i.path === p);
                        if (item) {
                            item.category = currentCategory;
                        }
                    });
                } else {
                    const item = itemsData.find(i => i.path === itemPath);
                    if (item) {
                        item.category = currentCategory;
                    }
                }
                renderItems();
            }
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function getCategoryBadgeStyle(cat) {
            if (cat === 'Мусор') return 'bg-red-900/50 text-red-300 border border-red-700/50';
            if (cat === 'Неизвестно') return 'bg-yellow-900/40 text-yellow-300 border border-yellow-700/40';
            if (cat === 'Несортированные') return 'bg-slate-700 text-slate-400 border border-slate-600';
            if (cat === 'Игры' || cat === 'Steam' || cat === 'Репаки') return 'bg-purple-900/50 text-purple-300 border border-purple-700/50';
            if (cat === 'Проекты' || cat === 'Софт' || cat === 'Прошивки') return 'bg-blue-900/50 text-blue-300 border border-blue-700/50';
            if (cat === 'Образы' || cat === 'Бэкапы') return 'bg-emerald-900/50 text-emerald-300 border border-emerald-700/50';
            if (cat === 'Музыка' || cat === 'Видео') return 'bg-amber-900/50 text-amber-300 border border-amber-700/50';
            return 'bg-cyan-900/50 text-cyan-300 border border-cyan-700/50';
        }

        function updateProgress() {
            const total = itemsData.length;
            const sorted = itemsData.filter(i => i.category !== 'Несортированные').length;
            const percent = total > 0 ? Math.round((sorted / total) * 100) : 0;
            document.getElementById('progressText').innerText = `${percent}%`;
            document.getElementById('progressBar').style.width = `${percent}%`;
        }

        function renderItems() {
            const list = document.getElementById('itemList');
            document.getElementById('itemCount').innerText = itemsData.length;
            updateProgress();
            
            if (itemsData.length === 0) {
                list.innerHTML = `<p class="text-slate-500 text-center py-20 text-sm">Папка пуста</p>`;
                return;
            }

            list.innerHTML = itemsData.map(i => {
                const safePath = i.path.replace(/"/g, '&quot;');
                const badgeStyle = getCategoryBadgeStyle(i.category);
                const isSorted = i.category !== 'Несортированные';
                
                return `
                    <div class="flex justify-between items-center p-2.5 rounded-lg ${isSorted ? 'bg-slate-900/30 opacity-75' : 'bg-slate-900/60'} hover:bg-slate-700/80 border border-slate-700/50 transition cursor-pointer item-row"
                         data-path="${safePath}"
                         data-isdir="${i.is_dir}">
                        <div class="truncate mr-3 flex items-center gap-2.5 flex-1 pointer-events-none">
                            <span class="text-lg">${i.is_dir ? '📁' : '📄'}</span>
                            <div class="truncate flex-1">
                                <p class="font-medium text-slate-200 text-xs md:text-sm truncate" title="${i.name}">${i.name}</p>
                                <p class="text-[11px] text-slate-500 truncate">${i.is_dir ? 'ЛКМ — категория | ПКМ — выделить в проводнике | Двойной — войти' : i.path}</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 shrink-0">
                            <span class="text-xs font-mono text-slate-400 pointer-events-none">${formatBytes(i.size)}</span>
                            <span class="px-2 py-0.5 rounded text-[11px] font-semibold transition pointer-events-none ${badgeStyle}">
                                ${i.category}
                            </span>
                        </div>
                    </div>
                `;
            }).join('');

            document.querySelectorAll('.item-row').forEach(row => {
                const path = row.getAttribute('data-path');
                const isDir = row.getAttribute('data-isdir') === 'true';

                row.addEventListener('click', () => {
                    assignCategory(path);
                });

                row.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    openItemInExplorer(path, e);
                });

                if (isDir) {
                    row.addEventListener('dblclick', (e) => {
                        e.stopPropagation();
                        loadDir(path);
                    });
                }
            });
        }

        async function openTextViewer() {
            const modal = document.getElementById('textModal');
            const contentBox = document.getElementById('textContent');
            modal.classList.remove('hidden');
            contentBox.innerText = "Загрузка отчёта...";
            try {
                const res = await fetch('/api/get-report-text');
                const text = await res.text();
                contentBox.innerText = text;
            } catch (err) {
                contentBox.innerText = "Ошибка загрузки отчёта.";
            }
        }
        function closeTextViewer() { document.getElementById('textModal').classList.add('hidden'); }

        function openSettings() { document.getElementById('settingsModal').classList.remove('hidden'); }
        function closeSettings() { document.getElementById('settingsModal').classList.add('hidden'); }

        function toggleMediaBar(enabled) {
            localStorage.setItem('mediaBar', enabled);
            applyMediaBarState(enabled);
        }
        function applyMediaBarState(enabled) {
            const bar = document.getElementById('mediaBar');
            if (enabled) bar.classList.remove('hidden');
            else bar.classList.add('hidden');
        }

        function toggleProgressBar(enabled) {
            localStorage.setItem('progressBar', enabled);
            applyProgressBarState(enabled);
        }
        function applyProgressBarState(enabled) {
            const card = document.getElementById('progressCard');
            if (enabled) card.classList.remove('hidden');
            else card.classList.add('hidden');
        }

        function changeTheme(theme) {
            const body = document.getElementById('pageBody');
            const topPanel = document.getElementById('topPanel');
            const progressCard = document.getElementById('progressCard');
            const catPanel = document.getElementById('catPanel');
            const listPanel = document.getElementById('listPanel');
            const mediaBar = document.getElementById('mediaBar');
            const mainTitle = document.getElementById('mainTitle');
            const activeCategory = document.getElementById('activeCategory');

            if (theme === 'cyberpunk') {
                body.className = "bg-zinc-950 text-pink-100 p-3 md:p-6 transition-colors duration-300";
                mainTitle.className = "text-xl md:text-2xl font-bold text-pink-500 font-mono tracking-wider transition-colors";
                activeCategory.className = "font-bold text-pink-400 text-sm transition-colors";
                topPanel.className = "bg-zinc-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-pink-500/40 flex flex-wrap gap-3 items-center transition-colors";
                progressCard.className = "bg-zinc-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-pink-500/40 transition-colors";
                catPanel.className = "bg-zinc-900/90 backdrop-blur p-3 rounded-xl space-y-1 shadow-lg border border-pink-500/40 transition-colors";
                listPanel.className = "lg:col-span-3 bg-zinc-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-pink-500/40 flex flex-col h-[550px] md:h-[620px] transition-colors";
                mediaBar.className = "fixed bottom-0 left-0 right-0 bg-black/95 backdrop-blur border-t border-pink-900/50 p-2.5 shadow-2xl z-40 transition-colors";
            } else if (theme === 'matrix') {
                body.className = "bg-black text-emerald-100 p-3 md:p-6 transition-colors duration-300";
                mainTitle.className = "text-xl md:text-2xl font-bold text-emerald-400 font-mono transition-colors";
                activeCategory.className = "font-bold text-emerald-300 text-sm transition-colors";
                topPanel.className = "bg-zinc-950/90 backdrop-blur p-3 rounded-xl shadow-lg border border-emerald-500/40 flex flex-wrap gap-3 items-center transition-colors";
                progressCard.className = "bg-zinc-950/90 backdrop-blur p-3 rounded-xl shadow-lg border border-emerald-500/40 transition-colors";
                catPanel.className = "bg-zinc-950/90 backdrop-blur p-3 rounded-xl space-y-1 shadow-lg border border-emerald-500/40 transition-colors";
                listPanel.className = "lg:col-span-3 bg-zinc-950/90 backdrop-blur p-3 rounded-xl shadow-lg border border-emerald-500/40 flex flex-col h-[550px] md:h-[620px] transition-colors";
                mediaBar.className = "fixed bottom-0 left-0 right-0 bg-black/95 backdrop-blur border-t border-emerald-950 p-2.5 shadow-2xl z-40 transition-colors";
            } else if (theme === 'sunset') {
                body.className = "bg-purple-950 text-orange-100 p-3 md:p-6 transition-colors duration-300";
                mainTitle.className = "text-xl md:text-2xl font-bold text-orange-400 transition-colors";
                activeCategory.className = "font-bold text-orange-300 text-sm transition-colors";
                topPanel.className = "bg-purple-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-orange-500/40 flex flex-wrap gap-3 items-center transition-colors";
                progressCard.className = "bg-purple-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-orange-500/40 transition-colors";
                catPanel.className = "bg-purple-900/90 backdrop-blur p-3 rounded-xl space-y-1 shadow-lg border border-orange-500/40 transition-colors";
                listPanel.className = "lg:col-span-3 bg-purple-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-orange-500/40 flex flex-col h-[550px] md:h-[620px] transition-colors";
                mediaBar.className = "fixed bottom-0 left-0 right-0 bg-purple-950/95 backdrop-blur border-t border-orange-950 p-2.5 shadow-2xl z-40 transition-colors";
            } else if (theme === 'monochrome') {
                body.className = "bg-neutral-900 text-neutral-100 p-3 md:p-6 transition-colors duration-300";
                mainTitle.className = "text-xl md:text-2xl font-bold text-neutral-200 transition-colors";
                activeCategory.className = "font-bold text-neutral-300 text-sm transition-colors";
                topPanel.className = "bg-neutral-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-neutral-700 flex flex-wrap gap-3 items-center transition-colors";
                progressCard.className = "bg-neutral-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-neutral-700 transition-colors";
                catPanel.className = "bg-neutral-800/90 backdrop-blur p-3 rounded-xl space-y-1 shadow-lg border border-neutral-700 transition-colors";
                listPanel.className = "lg:col-span-3 bg-neutral-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-neutral-700 flex flex-col h-[550px] md:h-[620px] transition-colors";
                mediaBar.className = "fixed bottom-0 left-0 right-0 bg-neutral-950/95 backdrop-blur border-t border-neutral-800 p-2.5 shadow-2xl z-40 transition-colors";
            } else if (theme === 'winter') {
                body.className = "bg-sky-950 text-sky-100 p-3 md:p-6 transition-colors duration-300";
                mainTitle.className = "text-xl md:text-2xl font-bold text-sky-300 transition-colors";
                activeCategory.className = "font-bold text-sky-200 text-sm transition-colors";
                topPanel.className = "bg-sky-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-sky-700/50 flex flex-wrap gap-3 items-center transition-colors";
                progressCard.className = "bg-sky-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-sky-700/50 transition-colors";
                catPanel.className = "bg-sky-900/90 backdrop-blur p-3 rounded-xl space-y-1 shadow-lg border border-sky-700/50 transition-colors";
                listPanel.className = "lg:col-span-3 bg-sky-900/90 backdrop-blur p-3 rounded-xl shadow-lg border border-sky-700/50 flex flex-col h-[550px] md:h-[620px] transition-colors";
                mediaBar.className = "fixed bottom-0 left-0 right-0 bg-sky-950/95 backdrop-blur border-t border-sky-900 p-2.5 shadow-2xl z-40 transition-colors";
            } else {
                body.className = "bg-slate-900 text-slate-100 p-3 md:p-6 transition-colors duration-300";
                mainTitle.className = "text-xl md:text-2xl font-bold text-cyan-400 transition-colors";
                activeCategory.className = "font-bold text-cyan-400 text-sm transition-colors";
                topPanel.className = "bg-slate-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-slate-700/65 flex flex-wrap gap-3 items-center transition-colors";
                progressCard.className = "bg-slate-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-slate-700/65 transition-colors";
                catPanel.className = "bg-slate-800/90 backdrop-blur p-3 rounded-xl space-y-1 shadow-lg border border-slate-700/65 transition-colors";
                listPanel.className = "lg:col-span-3 bg-slate-800/90 backdrop-blur p-3 rounded-xl shadow-lg border border-slate-700/65 flex flex-col h-[550px] md:h-[620px] transition-colors";
                mediaBar.className = "fixed bottom-0 left-0 right-0 bg-slate-950/95 backdrop-blur border-t border-slate-800 p-2.5 shadow-2xl z-40 transition-colors";
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.get("/api/browse")
async def browse_directory(path: str):
    if not path:
        raise HTTPException(status_code=400, detail="Путь не указан")
    
    target_path = Path(path.strip('"'))
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Указанный путь не существует или это не папка")
    
    manifest = load_manifest()
    items = []
    
    try:
        for entry in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            str_path = str(entry.resolve())
            is_dir = entry.is_dir()
            
            size = 0
            if not is_dir:
                try:
                    size = entry.stat().st_size
                except Exception:
                    size = 0
                    
            saved_category = manifest.get(str_path, "Несортированные")
                    
            items.append({
                "path": str_path,
                "name": entry.name,
                "is_dir": is_dir,
                "size": size,
                "category": saved_category
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения папки: {str(e)}")
        
    return {
        "current_path": str(target_path.resolve()),
        "parent_path": str(target_path.parent.resolve()) if target_path.parent != target_path else None,
        "items": items
    }

@app.post("/api/sort")
async def sort_item(action: SortAction):
    manifest = load_manifest()
    target_p = Path(action.item_path)
    updated_paths = [action.item_path]

    if action.category == "Несортированные":
        keys_to_delete = [k for k in manifest.keys() if k == action.item_path or k.startswith(action.item_path + os.sep)]
        for k in keys_to_delete:
            del manifest[k]
        updated_paths = keys_to_delete
    else:
        manifest[action.item_path] = action.category
        if target_p.is_dir():
            try:
                for sub in target_p.rglob("*"):
                    sub_str = str(sub.resolve())
                    manifest[sub_str] = action.category
                    updated_paths.append(sub_str)
            except Exception as e:
                print(f"Ошибка каскада: {e}")

    save_manifest(manifest)
    return {"status": "success", "item": action.item_path, "category": action.category, "updated_paths": updated_paths}

@app.post("/api/open-explorer")
async def open_explorer(path: str):
    if not path:
        raise HTTPException(status_code=400, detail="Путь не указан")
    target = Path(path.strip('"'))
    if not target.exists():
        raise HTTPException(status_code=400, detail="Путь не существует")
    try:
        if target.is_file():
            os.system(f'explorer /select, "{target}"')
        else:
            os.startfile(target)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось открыть проводник: {str(e)}")

@app.post("/api/media-key")
async def media_key(data: MediaKeyAction):
    VK_CODES = {
        "next": 0xB0,
        "prev": 0xB1,
        "playpause": 0xB3,
        "mute": 0xAD,
        "voldown": 0xAE,
        "volup": 0xAF
    }
    vk = VK_CODES.get(data.action)
    if not vk:
        raise HTTPException(status_code=400, detail="Неизвестная команда")
    try:
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 0x0002, 0)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка эмуляции: {str(e)}")

@app.post("/api/save-report")
async def save_report():
    path = generate_report_file()
    if not path:
        raise HTTPException(status_code=500, detail="Не удалось создать файл отчёта")
    return {"status": "success", "path": path}

@app.get("/api/get-report-text")
async def get_report_text():
    path = generate_report_file()
    if not path or not os.path.exists(path):
        return "Отчёт пока пуст."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def find_free_port(start_port=8000, max_port=9000):
    for port in range(start_port, max_port):
        for host in ("127.0.0.1", "0.0.0.0"):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind((host, port))
                except OSError:
                    break
        else:
            return port
    return start_port

if __name__ == "__main__":
    import uvicorn
    
    if len(sys.argv) > 1:
        try:
            free_port = int(sys.argv[1])
        except ValueError:
            free_port = find_free_port(8000)
    else:
        free_port = find_free_port(8000)

    print(f"\n[🌐] Сервер успешно развёртывается по адресу: http://127.0.0.1:{free_port}\n")
    uvicorn.run(app, host="127.0.0.1", port=free_port)