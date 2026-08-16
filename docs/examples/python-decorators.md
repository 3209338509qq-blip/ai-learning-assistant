# Python 装饰器

## 什么是装饰器

装饰器是一个接收函数并返回新函数的可调用对象。它可以在不修改原函数代码的情况下，为函数增加额外的功能，例如日志记录、性能计时、权限校验等。

Python 中使用 @ 符号作为装饰器的语法糖。以下两种写法完全等价：

    @timer
    def foo():
        pass

    def foo():
        pass
    foo = timer(foo)

## 装饰器的实现原理

装饰器的本质是闭包。外层函数接收被装饰的函数作为参数，内层函数包装原函数并增加额外逻辑，最后返回内层函数。

一个简单的计时装饰器：

    import time

    def timer(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            print(f"耗时: {time.time() - start:.4f}s")
            return result
        return wrapper

    @timer
    def slow_add(a, b):
        time.sleep(0.1)
        return a + b

## 带参数的装饰器

如果装饰器本身需要参数（如 @repeat(3)），需要再包一层：

    def repeat(times):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for _ in range(times):
                    func(*args, **kwargs)
            return wrapper
        return decorator

## functools.wraps 的作用

使用 @functools.wraps(func) 可以保留原函数的元信息（如 __name__、__doc__）。否则被装饰后函数名会变成 wrapper，不利于调试。

## 常见易错点

1. 装饰器语法糖在函数定义时执行，而不是调用时执行
2. 忘记返回 wrapper 函数，导致被装饰函数返回 None
3. 多个装饰器叠加时，执行顺序是从下往上（离函数最近的先执行）
4. 类方法使用装饰器时要注意 self 参数的传递
5. 使用 @functools.wraps 保留原函数元信息，否则部分框架（如 Flask 路由）会报错
