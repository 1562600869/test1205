import sqlite3
from datetime import date

DB_FILE = 'football.db'


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            phone TEXT,
            position TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '可上场'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS injuries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            injury_date TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL,
            expected_recovery_date TEXT,
            recovered INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    ''')

    conn.commit()
    conn.close()


def get_all_players():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_player(nickname, phone, position, status='可上场'):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO players (nickname, phone, position, status) VALUES (?, ?, ?, ?)',
        (nickname, phone, position, status)
    )
    conn.commit()
    player_id = cursor.lastrowid
    conn.close()
    return player_id


def update_player(player_id, nickname, phone, position, status):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE players SET nickname=?, phone=?, position=?, status=? WHERE id=?',
        (nickname, phone, position, status, player_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_player(player_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM injuries WHERE player_id=?', (player_id,))
    cursor.execute('DELETE FROM players WHERE id=?', (player_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_player(player_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE id=?', (player_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def add_injury(player_id, injury_date, description, severity, expected_recovery_date):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        conn.execute('BEGIN')
        cursor.execute(
            'INSERT INTO injuries (player_id, injury_date, description, severity, expected_recovery_date) VALUES (?, ?, ?, ?, ?)',
            (player_id, injury_date, description, severity, expected_recovery_date)
        )
        cursor.execute(
            "UPDATE players SET status='伤停' WHERE id=?",
            (player_id,)
        )
        conn.commit()
        injury_id = cursor.lastrowid
        return injury_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def confirm_recovery(injury_id):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        conn.execute('BEGIN')
        cursor.execute('SELECT player_id FROM injuries WHERE id=?', (injury_id,))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return False

        player_id = row['player_id']
        cursor.execute('SELECT status FROM players WHERE id=?', (player_id,))
        player_row = cursor.fetchone()
        if not player_row or player_row['status'] != '伤停':
            conn.rollback()
            return False

        cursor.execute('UPDATE injuries SET recovered=1 WHERE id=?', (injury_id,))
        cursor.execute("UPDATE players SET status='可上场' WHERE id=?", (player_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_injured_players():
    today = date.today().isoformat()
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, i.id as injury_id, i.injury_date, i.description, 
               i.severity, i.expected_recovery_date
        FROM players p
        JOIN injuries i ON p.id = i.player_id
        WHERE p.status = '伤停' 
          AND i.recovered = 0
          AND (i.expected_recovery_date IS NULL OR i.expected_recovery_date >= ?)
        ORDER BY i.injury_date DESC
    ''', (today,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_monthly_injury_stats():
    today = date.today()
    month_start = date(today.year, today.month, 1).isoformat()
    next_month = today.month + 1
    next_year = today.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_end = date(next_year, next_month, 1).isoformat()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT severity, COUNT(*) as count
        FROM injuries
        WHERE injury_date >= ? AND injury_date < ?
        GROUP BY severity
    ''', (month_start, month_end))
    rows = cursor.fetchall()
    conn.close()

    stats = {'轻微': 0, '中度': 0, '严重': 0}
    for row in rows:
        if row['severity'] in stats:
            stats[row['severity']] = row['count']
    return stats


def get_player_injuries(player_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM injuries 
        WHERE player_id=? 
        ORDER BY injury_date DESC
    ''', (player_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
