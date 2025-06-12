def status_color(status):
    return {
        'uploaded': 'secondary',
        'parsed': 'info',
        'translated': 'success',
        'completed': 'warning'
    }.get(status, 'light')

def status_display(status):
    return {
        'uploaded': '已上传',
        'parsed': '已解析',
        'translated': '已翻译',
        'completed': '已完成'
    }.get(status, status)