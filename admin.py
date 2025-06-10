#!/usr/bin/env python3
# coding: utf-8

import base64
import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# --- Конфигурация ---
app = Flask(__name__)
# ЗАМЕНИТЕ НА ВАШ СЕКРЕТНЫЙ КЛЮЧ
app.secret_key = 'your-secret-key-here' 
DATABASE_PATH = "vpn_users.db"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# --------------------

# HTML шаблон для админ-панели
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Admin Panel</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background-color: #f4f7f9; color: #333; }
        .container { max-width: 900px; margin: 40px auto; padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1, h2 { color: #0056b3; }
        h1 { text-align: center; }
        .card { background-color: #fdfdfd; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], textarea { width: calc(100% - 20px); padding: 10px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 15px; }
        textarea { min-height: 80px; }
        .btn { padding: 10px 15px; border: none; border-radius: 4px; color: #fff; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-primary { background-color: #007bff; }
        .btn-secondary { background-color: #6c757d; }
        .btn-danger { background-color: #dc3545; }
        .key-block { border: 1px dashed #ccc; padding: 15px; border-radius: 5px; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #007bff; color: white; }
        .flash { padding: 15px; margin-bottom: 20px; border-radius: 4px; }
        .flash.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
<div class="container">
    <h1>🛡️ VPN Admin Panel</h1>
    <h2>Управление VPN ключами пользователей</h2>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="card">
        <h3>Добавить/Редактировать пользователя</h3>
        <form action="{{ url_for('add_or_update_user') }}" method="post" enctype="multipart/form-data">
            <label for="user_identifier">User ID или @username *</label>
            <input type="text" id="user_identifier" name="user_identifier" placeholder="Telegram User ID или @username" required>
            
            <label for="display_name">Имя пользователя (для отображения)</label>
            <input type="text" id="display_name" name="display_name" placeholder="Имя для админ-панели">

            <div id="keys-container">
                <div class="key-block">
                    <h4>Ключ 1</h4>
                    <label>VPN Ключ *</label>
                    <textarea name="vpn_keys[]" placeholder="Вставьте VPN ключ здесь..." required></textarea>
                    <label>QR код (изображение)</label>
                    <input type="file" name="qr_images[]" accept=".png,.jpg,.jpeg">
                </div>
            </div>
            <button type="button" class="btn btn-secondary" onclick="addKeyField()">+ Добавить ключ</button>
            <br><br>
            <button type="submit" class="btn btn-primary">💾 Сохранить</button>
        </form>
    </div>

    <div class="card">
        <h3>Существующие пользователи</h3>
        <table>
            <thead>
                <tr>
                    <th>User ID / Username</th>
                    <th>Имя</th>
                    <th>Количество ключей</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
            {% for user in users %}
                <tr>
                    <td>{{ user.user_id }}</td>
                    <td>{{ user.username or 'Не указано' }}</td>
                    <td>{{ user.key_count }}</td>
                    <td>
                        <button class="btn btn-danger" onclick="deleteUser('{{ user.user_id }}')">Удалить</button>
                    </td>
                </tr>
            {% else %}
                <tr>
                    <td colspan="4" style="text-align:center;">Пользователи не найдены.</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
</div>
<script>
    let keyCounter = 1;
    function addKeyField() {
        keyCounter++;
        const container = document.getElementById('keys-container');
        const newKeyBlock = document.createElement('div');
        newKeyBlock.className = 'key-block';
        newKeyBlock.innerHTML = \`
            <h4>Ключ \${keyCounter}</h4>
            <label>VPN Ключ *</label>
            <textarea name="vpn_keys[]" placeholder="Вставьте VPN ключ здесь..." required></textarea>
            <label>QR код (изображение)</label>
            <input type="file" name="qr_images[]" accept=".png,.jpg,.jpeg">
        \`;
        container.appendChild(newKeyBlock);
    }

    async function deleteUser(userId) {
        if (confirm(\`Вы уверены, что хотите удалить пользователя \${userId} и все его ключи?\`)) {
            const response = await fetch('{{ url_for('delete_user') }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId })
            });
            const result = await response.json();
            if (result.success) {
                window.location.reload();
            } else {
                alert('Ошибка при удалении пользователя.');
            }
        }
    }
</script>
</body>
</html>
"""

def init_database():
    """Инициализация базы данных и создание таблицы, если она не существует."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vpn_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT,
            key_text TEXT NOT NULL,
            qr_image BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def allowed_file(filename):
    """Проверка, является ли расширение файла разрешенным."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_all_users():
    """Получение списка всех пользователей с количеством ключей."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, COUNT(id) as key_count 
        FROM vpn_keys 
        GROUP BY user_id, username 
        ORDER BY created_at DESC
    ''')
    users = [{'user_id': row[0], 'username': row[1], 'key_count': row[2]} for row in cursor.fetchall()]
    conn.close()
    return users

@app.route('/')
def admin_panel():
    """Главная страница административного интерфейса."""
    users = get_all_users()
    return render_template_string(ADMIN_TEMPLATE, users=users)

@app.route('/add_update_user', methods=['POST'])
def add_or_update_user():
    """Добавление или обновление ключей пользователя."""
    user_identifier = request.form.get('user_identifier')
    display_name = request.form.get('display_name')
    vpn_keys = request.form.getlist('vpn_keys[]')
    qr_files = request.files.getlist('qr_images[]')

    if not user_identifier or not any(key.strip() for key in vpn_keys):
        flash('User ID/Username и хотя бы один ключ являются обязательными полями!', 'error')
        return redirect(url_for('admin_panel'))

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Удаление существующих ключей для этого пользователя для полного обновления
    cursor.execute('DELETE FROM vpn_keys WHERE user_id = ?', (user_identifier,))
    
    # Добавление новых ключей
    for i, key_text in enumerate(vpn_keys):
        if key_text.strip():  # Пропускаем пустые поля для ключей
            qr_image_data = None
            if i < len(qr_files) and qr_files[i] and allowed_file(qr_files[i].filename):
                qr_image_data = qr_files[i].read()
            
            # Если display_name пуст, используем user_identifier, если это @username
            username_to_db = display_name if display_name else (user_identifier if user_identifier.startswith('@') else None)
            
            cursor.execute('''
                INSERT INTO vpn_keys (user_id, username, key_text, qr_image) 
                VALUES (?, ?, ?, ?)
            ''', (user_identifier, username_to_db, key_text.strip(), qr_image_data))

    conn.commit()
    conn.close()
    flash('Ключи пользователя успешно сохранены!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/delete_user', methods=['POST'])
def delete_user():
    """Удаление пользователя и всех его ключей."""
    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID not provided'}), 400
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vpn_keys WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    init_database()
    # Запуск приложения на всех интерфейсах для доступа извне
    app.run(debug=True, host='0.0.0.0', port=5000)
