# _init_

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

WIN = sys.platform.startswith('win')
if WIN: # 如果是 Windows 系统，使用三个斜线
    prefix = 'sqlite:///'
else: # 否则使用四个斜线
    prefix = 'sqlite:////'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # 关闭对模型修改的监控
app.config['SECRET_KEY'] = 'dev' # 等同于 app.secret_key = 'dev'

# 在扩展类实例化前加载配置
db = SQLAlchemy(app)
## 初始化 Flask-Login
login_manager = LoginManager(app) # 实例化扩展类

@login_manager.user_loader
def load_user(user_id): # 创建用户加载回调函数，接受用户 ID 作为参数
    user = User.query.get(int(user_id)) # 用 ID 作为 User 模型的主键查询对应的用户
    return user # 返回用户对象
login_manager.login_view = 'login' # 把 login_manager.login_view 的值设为我们程序的登录视图端点

# 模板上下文处理函数，后面我们创建的任意一个模板，都可以在模板中直接使用 user 变量
@app.context_processor
def inject_user(): # 函数名可以随意修改
    user = User.query.first()
    return dict(user=user) # 需要返回字典，等同于return {'user': user}











# models

# 存储用户信息的 User 模型类
# 添加 username 字段和 password_hash字段，分别用来存储登录所需的用户名和密码散列值
from werkzeug.security import generate_password_hash, check_password_hash
## 存储用户的 User 模型类继承 Flask-Login 提供的 UserMixin
from flask_login import UserMixin
class User(db.Model, UserMixin):  # 表名将会是 user（自动生成，小写处理）
    id = db.Column(db.Integer, primary_key=True) # 主键
    name = db.Column(db.String(20))
    username = db.Column(db.String(20)) # 用户名
    password_hash = db.Column(db.String(128)) # 密码散列值
    def set_password(self, password): # 用来设置密码的方法，接受密码作为参数
        self.password_hash = generate_password_hash(password) #将生成的密码保持到对应字段
    def validate_password(self, password): # 用于验证密码的方法，接受密码作为参数
        return check_password_hash(self.password_hash, password)
# 存储电影信息的 Movie 模型类
class Movie(db.Model): # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True) # 主键
    title = db.Column(db.String(60)) # 电影标题
    date = db.Column(db.DateTime) # 上映时间
    country = db.Column(db.String(60)) # 上映国家
    type = db.Column(db.String(60)) # 电影类型
    year = db.Column(db.String(4)) # 电影年份
    box = db.Column(db.Float) # 票房
    relations = db.relationship('Relation', back_populates='movie')
    # relation = db.relationship('Relation', primaryjoin='relation.movie_id == movie.id',
    #                         backref='movie', uselist=False, lazy='select') 
# 储存演员信息的 Actor 模型类
class Actor(db.Model): # 表名将会是 actor
    id = db.Column(db.Integer, primary_key=True) # 主键
    name = db.Column(db.String(60)) # 演员名称
    gender = db.Column(db.String(10)) # 演员性别，设为10是防止外国的少数性别
    country = db.Column(db.String(60)) # 演员国籍
    relations = db.relationship('Relation', back_populates='actor')
    # relation = db.relationship('Relation', primaryjoin='relation.actor_id == actor.id',
    #                         backref='actor', uselist=False, lazy='select')
# 储存电影-演员信息的 Relation 模型类
class Relation(db.Model): # 表名将会是 relation
    id = db.Column(db.Integer, primary_key=True) # 主键
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id')) # 外键
    actor_id = db.Column(db.Integer, db.ForeignKey('actor.id')) # 外键
    type = db.Column(db.String(6)) # 关系类型 
    movie = db.relationship('Movie', back_populates='relations')
    actor = db.relationship('Actor', back_populates='relations')












# views

from flask import render_template, request, url_for, redirect, flash
from flask_login import login_user, login_required, logout_user, current_user
# 在主页视图读取数据库记录
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST': # 判断是否是 POST 请求
        if not current_user.is_authenticated: # 如果当前用户未认证
            return redirect(url_for('index')) # 重定向到主页
    movies = Movie.query.all()
    actors = Actor.query.all()
    user = User.query.first()
    return render_template('index.html', user=user, movies=movies, actors=actors)
# 注：在 index 视图中，原来传入模板的 name 变量被 user 实例取代，模板 index.html 中的两处 name 变量也要相应的更新为 user.name 属性
# 录入电影条目
@app.route('/movie/input', methods=['GET', 'POST'])
def input():
    if request.method == 'POST':
        # 电影
        title = request.form.get('title')
        year = request.form.get('year')
        country = request.form.get('country')
        type = request.form.get('type')
        box = request.form.get('box')
        
        existing_movie = Movie.query.filter_by(title=title).first()
        if existing_movie: # 检查电影是否已经存在
            flash('The movie has already existed!')
            return redirect(url_for('input'))
        if not title or not year or len(year) > 4 or len(title) > 60 or len(country) > 60 or len(type) > 60:
            flash('Invalid input.') # 显示错误提示
            return redirect(url_for('index')) # 重定向回主页
        if box == '':  # 处理票房为空的情况
            box = None
        
        movie = Movie(title=title, year=year, country=country, type=type, box=box)
        db.session.add(movie)
        
        # 主演、导演
        director_name = request.form.get('director_name')
        actor_name = request.form.get('actor_name')
        
        if director_name == '' and actor_name == '':
            director_name = None
            actor_name = None
        elif  director_name == '' and actor_name != '':
            actor = Actor(name = actor_name, gender = None, country = None)
            db.session.add(actor)
        elif  director_name != '' and actor_name == '':
            director = Actor(name = director_name, gender = None, country = None)
            db.session.add(director)
        elif  director_name != '' and actor_name != '' and director_name != actor_name:
            actor = Actor(name = actor_name, gender = None, country = None)
            director = Actor(name = director_name, gender = None, country = None)
            db.session.add(actor)
            db.session.add(director)
        elif director_name != '' and actor_name != '' and director_name == actor_name:
            actor = Actor(name = actor_name, gender = None, country = None)
            db.session.add(actor)
        
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('input.html')
# 编辑电影条目
@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required # 登录保护
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if request.method == 'POST': # 处理编辑表单的提交请求
        title = request.form['title']
        year = request.form['year']
        country = request.form['country']
        type = request.form['type']
        box = request.form['box']
        if not title or not year or len(year) > 4 or len(title) > 60 or len(country) > 60 or len(type) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))
        # 重定向回对应的编辑页面
        movie.title = title
        movie.year = year
        movie.country = country
        movie.type = type 
        movie.box = box
        db.session.commit() # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index')) # 重定向回主页
    return render_template('edit.html', movie=movie) # 传入被编辑的电影记录
# 删除电影条目
@app.route('/movie/delete/<int:movie_id>', methods=['POST']) # 限定只接受 POST 请求
@login_required # 登录保护
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id) # 获取电影记录
    db.session.delete(movie) # 删除对应的记录
    db.session.commit() # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index')) # 重定向回主页
# 查询电影条目
@app.route('/search', methods=['GET'])
def search():
    # 根据搜索查询查询电影
    search_query = request.args.get('search_query', '')
    search_results = Movie.query.filter(Movie.title.ilike(f'%{search_query}%')).all()
    return render_template('search.html', search_results=search_results)

# 录入演员条目
@app.route('/actor/input_actor', methods=['GET', 'POST'])
def input_actor():
    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        country = request.form.get('country')
        # 验证数据
        if not name or not gender or not country or len(gender) > 10 or len(name) > 60 or len(country) > 60:
            flash('Invalid input.') # 显示错误提示
            return redirect(url_for('index')) # 重定向回主页
        actor = Actor(name=name, gender=gender, country=country)
        db.session.add(actor)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('input_actor.html')
#编辑演员条目
@app.route('/actor/edit_actor/<int:actor_id>', methods=['GET', 'POST'])
@login_required # 登录保护
def edit_actor(actor_id):
    actor = Actor.query.get_or_404(actor_id)
    if request.method == 'POST': # 处理编辑表单的提交请求
        name = request.form['name']
        gender = request.form['gender']
        country = request.form['country']
        if not name or not gender or not country or len(gender) > 10 or len(name) > 60 or len(country) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit_actor', actor_id=actor_id))
        
        # 重定向回对应的编辑页面
        actor.name = name # 更新标题
        actor.gender = gender # 更新年份
        actor.country = country # 更新国家
        db.session.commit() # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index')) # 重定向回主页
    return render_template('edit_actor.html', actor=actor) # 传入被编辑的电影记录
# 删除演员条目
@app.route('/actor/delete_actor/<int:actor_id>', methods=['POST']) # 限定只接受 POST 请求
@login_required # 登录保护
def delete_actor(actor_id):
    actor = Actor.query.get_or_404(actor_id) # 获取电影记录
    db.session.delete(actor) # 删除对应的记录
    db.session.commit() # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index')) # 重定向回主页
# 查询演员条目
@app.route('/search_actor', methods=['GET'])
def search_actor():
    # 根据搜索查询查询电影
    search_query = request.args.get('search_query', '')
    search_results = Actor.query.filter(Actor.name.ilike(f'%{search_query}%')).all()
    return render_template('search_actor.html', search_results=search_results)

# 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))
        user = User.query.first()
        # 验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user) # 登入用户
            flash('Login success.')
            return redirect(url_for('index')) # 重定向到主页
        flash('Invalid username or password.') # 如果验证失败，显示错误消息
        return redirect(url_for('login')) # 重定向回登录页面
    return render_template('login.html')
# 用户登出
@app.route('/logout')
@login_required # 用于视图保护，后面会详细介绍
def logout():
    logout_user() # 登出用户
    flash('Goodbye.')
    return redirect(url_for('index')) # 重定向回首页
# 支持设置用户名字
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']
        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))
        current_user.name = name
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用法
        # user = User.query.first()
        # user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))
    return render_template('settings.html')











# commands

import click
# 编写自定义命令来自动执行创建数据库表操作
@app.cli.command() # 注册为命令
@click.option('--drop', is_flag=True, help='Create after drop.')
# 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop: # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.') # 输出提示信息
# 生成虚拟数据命令
import datetime
@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()
    # 全局的两个变量移动到这个函数内
    name = 'Buyan Sun'
    movies = [
        {'id': '1001', 'title': '战狼2', 'date': datetime.datetime(2017,7,27), 'country': '中国', 'type': '战争', 'year': '2017', 'box': 56.84}, 
        {'id': '1002', 'title': '哪吒之魔童降世', 'date': datetime.datetime(2019,7,26), 'country': '中国', 'type': '动画', 'year': '2019', 'box': 50.15}, 
        {'id': '1003', 'title': '流浪地球', 'date': datetime.datetime(2019,2,5), 'country': '中国', 'type': '科幻', 'year': '2019', 'box': 46.86}, 
        {'id': '1004', 'title': '复仇者联盟4', 'date': datetime.datetime(2019,4,24), 'country': '美国', 'type': '科幻', 'year': '2019', 'box': 42.50}, 
        {'id': '1005', 'title': '红海行动', 'date': datetime.datetime(2018,2,16), 'country': '中国', 'type': '战争', 'year': '2018', 'box': 36.50}, 
        {'id': '1006', 'title': '唐人街探案2', 'date': datetime.datetime(2018,2,16), 'country': '中国', 'type': '喜剧', 'year': '2018', 'box': 33.97}, 
        {'id': '1007', 'title': '我不是药神', 'date': datetime.datetime(2018,7,5), 'country': '中国', 'type': '喜剧', 'year': '2018', 'box': 31.00}, 
        {'id': '1008', 'title': '中国机长', 'date': datetime.datetime(2019,9,30), 'country': '中国', 'type': '剧情', 'year': '2019', 'box': 29.12}, 
        {'id': '1009', 'title': '速度与激情8', 'date': datetime.datetime(2017,4,14), 'country': '美国', 'type': '动作', 'year': '2017', 'box': 26.70}, 
        {'id': '1010', 'title': '西虹市首富', 'date': datetime.datetime(2018,7,27), 'country': '中国', 'type': '喜剧', 'year': '2018', 'box': 25.47}, 
        {'id': '1011', 'title': '复仇者联盟3', 'date': datetime.datetime(2018,5,11), 'country': '美国', 'type': '科幻', 'year': '2018', 'box': 23.90}, 
        {'id': '1012', 'title': '捉妖记2', 'date': datetime.datetime(2018,2,16), 'country': '中国', 'type': '喜剧', 'year': '2018', 'box': 22.37}, 
        {'id': '1013', 'title': '八佰', 'date': datetime.datetime(2020,8,21), 'country': '中国', 'type': '战争', 'year': '2020', 'box': 30.10}, 
        {'id': '1014', 'title': '姜子牙', 'date': datetime.datetime(2020,10,1), 'country': '中国', 'type': '动画', 'year': '2020', 'box': 16.02}, 
        {'id': '1015', 'title': '我和我的家乡', 'date': datetime.datetime(2020,10,1), 'country': '中国', 'type': '剧情', 'year': '2020', 'box': 28.29}, 
        {'id': '1016', 'title': '你好，李焕英', 'date': datetime.datetime(2021,2,12), 'country': '中国', 'type': '喜剧', 'year': '2021', 'box': 54.13}, 
        {'id': '1017', 'title': '长津湖', 'date': datetime.datetime(2021,9,30), 'country': '中国', 'type': '战争', 'year': '2021', 'box': 53.48}, 
        {'id': '1018', 'title': '速度与激情9', 'date': datetime.datetime(2021,5,21), 'country': '中国', 'type': '动作', 'year': '2021', 'box': 13.92}, 
]
    actors = [
        {'id': '2001', 'name': '吴京', 'gender': '男', 'country': '中国'}, 
        {'id': '2002', 'name': '饺子', 'gender': '男', 'country': '中国'}, 
        {'id': '2003', 'name': '屈楚萧', 'gender': '男', 'country': '中国'}, 
        {'id': '2004', 'name': '郭帆', 'gender': '男', 'country': '中国'}, 
        {'id': '2005', 'name': '乔罗素', 'gender': '男', 'country': '美国'}, 
        {'id': '2006', 'name': '小罗伯特·唐尼', 'gender': '男', 'country': '美国'}, 
        {'id': '2007', 'name': '克里斯·埃文斯', 'gender': '男', 'country': '美国'}, 
        {'id': '2008', 'name': '林超贤', 'gender': '男', 'country': '中国'}, 
        {'id': '2009', 'name': '张译', 'gender': '男', 'country': '中国'}, 
        {'id': '2010', 'name': '黄景瑜', 'gender': '男', 'country': '中国'}, 
        {'id': '2011', 'name': '陈思诚', 'gender': '男', 'country': '中国'}, 
        {'id': '2012', 'name': '王宝强', 'gender': '男', 'country': '中国'}, 
        {'id': '2013', 'name': '刘昊然', 'gender': '男', 'country': '中国'}, 
        {'id': '2014', 'name': '文牧野', 'gender': '男', 'country': '中国'}, 
        {'id': '2015', 'name': '徐峥', 'gender': '男', 'country': '中国'}, 
        {'id': '2016', 'name': '刘伟强', 'gender': '男', 'country': '中国'}, 
        {'id': '2017', 'name': '张涵予', 'gender': '男', 'country': '中国'}, 
        {'id': '2018', 'name': 'F·加里·格雷', 'gender': '男', 'country': '美国'}, 
        {'id': '2019', 'name': '范·迪塞尔', 'gender': '男', 'country': '美国'}, 
        {'id': '2020', 'name': '杰森·斯坦森', 'gender': '男', 'country': '美国'}, 
        {'id': '2021', 'name': '闫非', 'gender': '男', 'country': '中国'}, 
        {'id': '2022', 'name': '沈腾', 'gender': '男', 'country': '中国'}, 
        {'id': '2023', 'name': '安东尼·罗素', 'gender': '男', 'country': '美国'}, 
        {'id': '2024', 'name': '克里斯·海姆斯沃斯', 'gender': '男', 'country': '美国'}, 
        {'id': '2025', 'name': '许诚毅', 'gender': '男', 'country': '中国'}, 
        {'id': '2026', 'name': '梁朝伟', 'gender': '男', 'country': '中国'}, 
        {'id': '2027', 'name': '白百何', 'gender': '女', 'country': '中国'}, 
        {'id': '2028', 'name': '井柏然', 'gender': '男', 'country': '中国'}, 
        {'id': '2029', 'name': '管虎', 'gender': '男', 'country': '中国'}, 
        {'id': '2030', 'name': '王千源', 'gender': '男', 'country': '中国'}, 
        {'id': '2031', 'name': '姜武', 'gender': '男', 'country': '中国'}, 
        {'id': '2032', 'name': '宁浩', 'gender': '男', 'country': '中国'}, 
        {'id': '2033', 'name': '葛优', 'gender': '男', 'country': '中国'}, 
        {'id': '2034', 'name': '范伟', 'gender': '男', 'country': '中国'}, 
        {'id': '2035', 'name': '贾玲', 'gender': '女', 'country': '中国'}, 
        {'id': '2036', 'name': '张小斐', 'gender': '女', 'country': '中国'}, 
        {'id': '2037', 'name': '陈凯歌', 'gender': '男', 'country': '中国'}, 
        {'id': '2038', 'name': '徐克', 'gender': '男', 'country': '中国'}, 
        {'id': '2039', 'name': '易烊千玺', 'gender': '男', 'country': '中国'}, 
        {'id': '2040', 'name': '林诣彬', 'gender': '男', 'country': '美国'}, 
        {'id': '2041', 'name': '米歇尔·罗德里格兹', 'gender': '女', 'country': '美国'},
    ]
    relation = [
        {'id': '1', 'movie_id': '1001', 'actor_id': '2001', 'type': '主演'}, 
        {'id': '10', 'movie_id': '1005', 'actor_id': '2008', 'type': '导演'}, 
        {'id': '11', 'movie_id': '1005', 'actor_id': '2009', 'type': '主演'}, 
        {'id': '12', 'movie_id': '1005', 'actor_id': '2010', 'type': '主演'}, 
        {'id': '13', 'movie_id': '1006', 'actor_id': '2011', 'type': '导演'}, 
        {'id': '14', 'movie_id': '1006', 'actor_id': '2012', 'type': '主演'}, 
        {'id': '15', 'movie_id': '1006', 'actor_id': '2013', 'type': '主演'}, 
        {'id': '16', 'movie_id': '1007', 'actor_id': '2014', 'type': '导演'}, 
        {'id': '17', 'movie_id': '1007', 'actor_id': '2015', 'type': '主演'}, 
        {'id': '18', 'movie_id': '1008', 'actor_id': '2016', 'type': '导演'}, 
        {'id': '19', 'movie_id': '1008', 'actor_id': '2017', 'type': '主演'}, 
        {'id': '2', 'movie_id': '1001', 'actor_id': '2001', 'type': '导演'}, 
        {'id': '20', 'movie_id': '1009', 'actor_id': '2018', 'type': '导演'}, 
        {'id': '21', 'movie_id': '1009', 'actor_id': '2019', 'type': '主演'}, 
        {'id': '22', 'movie_id': '1009', 'actor_id': '2020', 'type': '主演'}, 
        {'id': '23', 'movie_id': '1010', 'actor_id': '2021', 'type': '导演'}, 
        {'id': '24', 'movie_id': '1010', 'actor_id': '2022', 'type': '主演'}, 
        {'id': '25', 'movie_id': '1011', 'actor_id': '2023', 'type': '导演'}, 
        {'id': '26', 'movie_id': '1011', 'actor_id': '2006', 'type': '主演'}, 
        {'id': '27', 'movie_id': '1011', 'actor_id': '2024', 'type': '主演'}, 
        {'id': '28', 'movie_id': '1012', 'actor_id': '2025', 'type': '导演'}, 
        {'id': '29', 'movie_id': '1012', 'actor_id': '2026', 'type': '主演'}, 
        {'id': '3', 'movie_id': '1002', 'actor_id': '2002', 'type': '导演'}, 
        {'id': '30', 'movie_id': '1012', 'actor_id': '2027', 'type': '主演'}, 
        {'id': '31', 'movie_id': '1012', 'actor_id': '2028', 'type': '主演'}, 
        {'id': '32', 'movie_id': '1013', 'actor_id': '2029', 'type': '导演'}, 
        {'id': '33', 'movie_id': '1013', 'actor_id': '2030', 'type': '主演'}, 
        {'id': '34', 'movie_id': '1013', 'actor_id': '2009', 'type': '主演'}, 
        {'id': '35', 'movie_id': '1013', 'actor_id': '2031', 'type': '主演'}, 
        {'id': '36', 'movie_id': '1015', 'actor_id': '2032', 'type': '导演'}, 
        {'id': '37', 'movie_id': '1015', 'actor_id': '2015', 'type': '导演'}, 
        {'id': '38', 'movie_id': '1015', 'actor_id': '2011', 'type': '导演'}, 
        {'id': '39', 'movie_id': '1015', 'actor_id': '2015', 'type': '主演'}, 
        {'id': '4', 'movie_id': '1003', 'actor_id': '2001', 'type': '主演'}, 
        {'id': '40', 'movie_id': '1015', 'actor_id': '2033', 'type': '主演'}, 
        {'id': '41', 'movie_id': '1015', 'actor_id': '2034', 'type': '主演'}, 
        {'id': '42', 'movie_id': '1016', 'actor_id': '2035', 'type': '导演'}, 
        {'id': '43', 'movie_id': '1016', 'actor_id': '2035', 'type': '主演'}, 
        {'id': '44', 'movie_id': '1016', 'actor_id': '2036', 'type': '主演'}, 
        {'id': '45', 'movie_id': '1016', 'actor_id': '2022', 'type': '主演'}, 
        {'id': '46', 'movie_id': '1017', 'actor_id': '2037', 'type': '导演'}, 
        {'id': '47', 'movie_id': '1017', 'actor_id': '2038', 'type': '导演'}, 
        {'id': '48', 'movie_id': '1017', 'actor_id': '2008', 'type': '导演'}, 
        {'id': '49', 'movie_id': '1017', 'actor_id': '2001', 'type': '主演'}, 
        {'id': '5', 'movie_id': '1003', 'actor_id': '2003', 'type': '主演'}, 
        {'id': '50', 'movie_id': '1017', 'actor_id': '2039', 'type': '主演'}, 
        {'id': '51', 'movie_id': '1018', 'actor_id': '2040', 'type': '导演'}, 
        {'id': '52', 'movie_id': '1018', 'actor_id': '2019', 'type': '主演'}, 
        {'id': '53', 'movie_id': '1018', 'actor_id': '2041', 'type': '主演'}, 
        {'id': '6', 'movie_id': '1003', 'actor_id': '2004', 'type': '导演'}, 
        {'id': '7', 'movie_id': '1004', 'actor_id': '2005', 'type': '导演'}, 
        {'id': '8', 'movie_id': '1004', 'actor_id': '2006', 'type': '主演'}, 
        {'id': '9', 'movie_id': '1004', 'actor_id': '2007', 'type': '主演'}, 
    ]
    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(id=m['id'], title=m['title'], date=m['date'], 
                      country=m['country'], type=m['type'], year=m['year'], box=m['box'])
        db.session.add(movie)
    for a in actors:
        actor = Actor(id=a['id'], name=a['name'], country=a['country'], gender=a['gender'])
        db.session.add(actor)
    for r in relation:
        relation = Relation(id=r['id'], movie_id=r['movie_id'], actor_id=r['actor_id'], type=r['type'])
        db.session.add(relation)
    db.session.commit()
    click.echo('Done.')
# 创建管理员账户命令
@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()
    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password) # 设置密码
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password) # 设置密码
        db.session.add(user)
    db.session.commit() # 提交数据库会话
    click.echo('Done.')











# errors

# 404 错误处理函数
@app.errorhandler(404)
def page_not_found(e): # 接受异常对象作为参数
    return render_template('errors/404.html'), 404 # 返回模板和状态码
# 400 错误处理函数
@app.errorhandler(400)
def page_not_found(e): # 接受异常对象作为参数
    return render_template('errors/400.html'), 400 # 返回模板和状态码
# 500 错误处理函数
@app.errorhandler(500)
def page_not_found(e): # 接受异常对象作为参数
    return render_template('errors/500.html'), 500 # 返回模板和状态码