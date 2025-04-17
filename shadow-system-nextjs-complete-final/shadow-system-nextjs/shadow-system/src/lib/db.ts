import { Pool } from 'pg';

// إعداد اتصال قاعدة البيانات
const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'shadow_system',
  password: process.env.DB_PASSWORD || 'postgres',
  port: parseInt(process.env.DB_PORT || '5432'),
});

// التحقق من الاتصال
pool.on('connect', () => {
  console.log('تم الاتصال بقاعدة البيانات بنجاح');
});

// دالة للتنفيذ المباشر للاستعلامات
export async function query(text: string, params?: any[]) {
  try {
    const start = Date.now();
    const res = await pool.query(text, params);
    const duration = Date.now() - start;
    console.log('تم تنفيذ الاستعلام', { text, duration, rows: res.rowCount });
    return res;
  } catch (error) {
    console.error('خطأ في تنفيذ الاستعلام:', error);
    throw error;
  }
}

// دالة لإنشاء الجداول إذا لم تكن موجودة
export async function initializeDatabase() {
  try {
    // إنشاء جدول المستخدمين
    await query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL,
        role VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // إنشاء جدول المحادثات
    await query(`
      CREATE TABLE IF NOT EXISTS conversations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        title VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // إنشاء جدول الرسائل
    await query(`
      CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        conversation_id INTEGER REFERENCES conversations(id),
        sender VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // إنشاء جدول الذاكرة العاطفية
    await query(`
      CREATE TABLE IF NOT EXISTS emotional_memory (
        id SERIAL PRIMARY KEY,
        key VARCHAR(100) NOT NULL,
        value TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    console.log('تم إنشاء الجداول بنجاح');

    // التحقق من وجود مستخدمين افتراضيين
    const usersResult = await query('SELECT * FROM users');
    
    if (usersResult.rowCount === 0) {
      // إضافة مستخدمين افتراضيين
      await query(`
        INSERT INTO users (username, password, role)
        VALUES 
          ('naseem', 'admin123', 'admin'),
          ('amir', 'assistant123', 'assistant')
      `);
      console.log('تم إضافة المستخدمين الافتراضيين');
    }

    return { success: true, message: 'تم تهيئة قاعدة البيانات بنجاح' };
  } catch (error) {
    console.error('خطأ في تهيئة قاعدة البيانات:', error);
    return { success: false, message: 'حدث خطأ أثناء تهيئة قاعدة البيانات', error };
  }
}

export default pool;
