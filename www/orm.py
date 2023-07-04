#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Luodayu'


import logging
import aiomysql

# 配置日志模块
logging.basicConfig(level=logging.INFO)


# 定义ORM框架的基本模型
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        table_name = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, table_name))
        mappings = dict()
        fields = []
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primary_key:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primary_key  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primary_key, ', '.join(escaped_fields), table_name)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
        table_name, ', '.join(escaped_fields), primary_key, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
        table_name, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (table_name, primary_key)
        return type.__new__(cls, name, bases, attrs)


# 定义字段类型
class Field(object):
    def __init__(self, name=None, column_type=None, primary_key=False, default=None):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 定义常用字段类型
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


# 创建参数字符串，用于SQL语句中的参数
def create_args_string(num):
    return ', '.join(['?' for i in range(num)])


# 定义ORM框架的基本操作
class Model(dict, metaclass=ModelMetaclass):

    # 初始化方法，接收关键字参数作为对象的属性
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    # 获取对象指定属性的值，如果不存在则返回None
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    # 设置对象指定属性的值
    def __setattr__(self, key, value):
        self[key] = value

    # 获取对象指定属性的值，如果不存在则返回None
    def get(self, key, default=None):
        return self[key] if key in self else default

    # 获取对象指定属性的值，如果不存在则返回None
    def getValue(self, key):
        return getattr(self, key, None)

    # 获取对象指定属性的值，如果不存在则返回默认值
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    # 根据主键查找对象
    @classmethod
    async def find(cls, pk):
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    # 查找所有对象
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    # 查找指定数量的对象
    @classmethod
    async def findNumber(cls, selectField='*', where=None, args=None):
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    # 插入对象到数据库中
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    # 更新对象到数据库中
    async def update(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    # 从数据库中删除对象
    async def remove(self):
        args = [self.getValueOrDefault(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)


# 执行SQL语句，返回结果集（多行）
async def select(sql, args, size=None):
    logging.info('SQL: %s ARGS: %s' % (sql.replace('?', '%s'), args))
    global __pool
    async with __pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs


# 执行SQL语句，返回结果数（单行）
async def execute(sql, args):
    logging.info('SQL: %s ARGS: %s' % (sql.replace('?', '%s'), args))
    global __pool
    async with __pool.acquire() as conn:
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            logging.info('affected rows: %s' % affected)
            return affected
        except BaseException as e:
            raise


# 创建全局连接池，供所有HTTP请求共享使用
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


# 关闭全局连接池
async def close_pool():
    global __pool
    if __pool is not None:
        __pool.close()
        await __pool.wait_closed()


# 初始化数据库连接池，在应用启动时调用
async def init_db(app):
    await create_pool(app.loop,
                      host='localhost',
                      port=3306,
                      user='root',
                      password='123456',
                      db='test')


# 关闭数据库连接池，在应用退出时调用
async def close_db(app):
    await close_pool()


# 测试代码示例：
# if __name__ == '__main__':
#     import asyncio
#
#     loop = asyncio.get_event_loop()
#
#
#     async def test():
#         class User(Model):
#             __table__ = 'user'
#
#             id = IntegerField(primary_key=True)
#             name = StringField()
#
#         await create_pool(loop=loop,
#                           host='localhost',
#                           port=3306,
#                           user='root',
#                           password='123456',
#                           db='test')
#
#         user1 = User(id=1, name='Tom')
#
#         await user1.save()
#
#         user2 = await User.find(1)
#
#         print(user2.name)
#
#         user3 = await User.findAll()
#
#         print(user3[0].name)
#
#
#     loop.run_until_complete(test())

