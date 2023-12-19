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


# 添加 username 字段和 password_hash字段，分别用来存储登录所需的用户名和密码散列值
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin  # 存储用户的 User 模型类继承 Flask-Login 提供的 UserMixin

# 存储用户信息的 User 模型类
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
        db.session.commit() # 这里不做这一步的话就不会给新的生成id
        movie_id = movie.id
        
        # 主演、导演
        director_name = request.form.get('director_name')
        actor_name = request.form.get('actor_name')
        
        existing_director = Actor.query.filter_by(name=director_name).first() # 查找主演是否已经存在
        existing_actor = Actor.query.filter_by(name=actor_name).first() # 查找导演是否已经存在
        
        if director_name == '' and actor_name == '':
            director_name = None
            actor_name = None
        elif director_name == '' and actor_name != '':
            if existing_actor:
                actor_id = existing_actor.id
                relation = Relation(movie_id=movie_id, actor_id=actor_id, type='主演')
                flash('The actor has already existed!')
            else:
                actor = Actor(name = actor_name, gender = None, country = None)
                db.session.add(actor)
                db.session.commit() # 这里不做这一步的话就不会给actor生成id
                actor_id = actor.id
                relation = Relation(movie_id=movie_id, actor_id=actor_id, type='主演')
            db.session.add(relation)
        elif director_name != '' and actor_name == '':
            if existing_director:
                director_id = existing_director.id
                relation = Relation(movie_id=movie_id, actor_id=director_id, type='导演')
                flash('The director has already existed!')
            else:
                director = Actor(name = director_name, gender = None, country = None)
                db.session.add(director)
                db.session.commit() # 这里不做这一步的话就不会给director生成id
                director_id = director.id
                relation = Relation(movie_id=movie_id, actor_id=director_id, type='导演')
            db.session.add(relation)
        elif director_name != '' and actor_name != '' and director_name != actor_name:
            
            if existing_actor:
                actor_id = existing_actor.id
                relation = Relation(movie_id=movie_id, actor_id=actor_id, type='主演')
                flash('The actor has already existed!')
                db.session.add(relation)
            else:
                actor = Actor(name = actor_name, gender = None, country = None)
                db.session.add(actor)
                db.session.commit() # 这里不做这一步的话就不会给新的生成id
                actor_id = actor.id
                relation = Relation(movie_id=movie_id, actor_id=actor_id, type='主演')
                db.session.add(relation)
                
            if existing_director:
                director_id = existing_director.id
                relation = Relation(movie_id=movie_id, actor_id=director_id, type='导演')
                flash('The director has already existed!')
            else:
                director = Actor(name = director_name, gender = None, country = None)
                db.session.add(director)
                db.session.commit() # 这里不做这一步的话就不会给新的生成id
                director_id = director.id
                relation = Relation(movie_id=movie_id, actor_id=director_id, type='导演')
                db.session.add(relation)
                
        elif director_name != '' and actor_name != '' and director_name == actor_name:
            if existing_actor:
                actor_id = existing_actor.id
                relation_actor = Relation(movie_id=movie_id, actor_id=actor_id, type='主演')
                relation_director = Relation(movie_id=movie_id, actor_id=actor_id, type='导演')
                flash('The actor has already existed!')
            else:
                actor = Actor(name = actor_name, gender = None, country = None)
                db.session.add(actor)
                db.session.commit() # 这里不做这一步的话就不会给新的生成id
                actor_id = actor.id
                relation_actor = Relation(movie_id=movie_id, actor_id=actor_id, type='主演')
                relation_director = Relation(movie_id=movie_id, actor_id=actor_id, type='导演')
            db.session.add(relation_actor)
            db.session.add(relation_director)
        
        # 提交更改
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('input.html')

# 编辑电影条目
@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required # 登录保护
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    actors = [] # 该电影的主演，以列表形式储存
    directors = [] # 该电影的导演，以列表形式储存
    relation_movie_actor = Relation.query.filter_by(movie_id=movie_id, type='主演').all() # 所有主演关系
    for relation in relation_movie_actor: # 不能用actors = [relation.actor for relation in relation_movie_actor]会有None
        actor = Actor.query.filter_by(id=relation.actor_id).first()
        if actor:
            actors.append(actor)
    relation_movie_director = Relation.query.filter_by(movie_id=movie_id, type='导演').all() # 所有导演关系
    for relation in relation_movie_director: # 不能用directors = [relation.actor for relation in relation_movie_director]
        director = Actor.query.filter_by(id=relation.actor_id).first()
        if director:
            directors.append(director)

            
    add_actor = Actor(name=None, gender=None, country=None) # 为了方便增添主演，如果没添就删了
    db.session.add(add_actor)
    add_actor_id = add_actor.id
    actors.append(add_actor)
    relation_movie_actor.append(Relation(movie_id=movie_id, actor_id=add_actor_id, type='主演'))
    
    add_director = Actor(name=None, gender=None, country=None) # 为了方便增添导演，如果没添就删了
    db.session.add(add_director)
    add_director_id = add_director.id
    directors.append(add_director)
    relation_movie_director.append(Relation(movie_id=movie_id, actor_id=add_director_id, type='主演'))
    
    
    if request.method == 'POST': # 处理编辑表单的提交请求
        title = request.form['title']
        year = request.form['year']
        country = request.form['country']
        type = request.form['type']
        box = request.form['box']
        if not title or not year or len(year) > 4 or len(title) > 60 or len(country) > 60 or len(type) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))
        if box == 'None': # 处理输入成字符串的情况
            box=None
        # 重定向回对应的编辑页面
        movie.title = title
        movie.year = year
        movie.country = country
        movie.type = type 
        movie.box = box
        
        for i, actor in enumerate(actors):
            actor_name_key = f'actor_name_{actor.id}'
            actor_name = request.form.get(actor_name_key, actor.name)
            existing_actor = Actor.query.filter_by(name=actor_name).first()
            relationship = Relation.query.filter_by(movie_id=movie_id, actor_id=actor.id).first()
            # relationship = relation_movie_actor[i]
            if existing_actor:
                if existing_actor.id == actor.id:
                    continue
                else:
                    if relationship: # 如果是空的就不执行
                        db.session.delete(relationship) # 删除对应的记录
                    db.session.add(Relation(movie_id=movie_id, actor_id=existing_actor.id, type='主演')) 
            else:
                new_actor = Actor(name=actor_name, gender=None, country=None)
                db.session.add(new_actor)
                db.session.commit() # 这里不做这一步的话就不会给new_actor生成id，不知道为什么
                if relationship: # 如果是空的就不执行
                    db.session.delete(relationship) # 删除对应的记录
                relationship = Relation(movie_id=movie_id, actor_id=new_actor.id, type='主演')
                db.session.add(relationship) 
                
        for i, director in enumerate(directors):
            director_name_key = f'director_name_{director.id}'
            director_name = request.form.get(director_name_key, director.name)
            existing_director = Actor.query.filter_by(name=director_name).first()
            relationship = Relation.query.filter_by(movie_id=movie_id, actor_id=director.id).first()
            if existing_director:
                if existing_director.id == director.id:
                    continue
                else:
                    if relationship: # 如果是空的就不执行
                        db.session.delete(relationship) # 删除对应的记录
                    db.session.add(Relation(movie_id=movie_id, actor_id=existing_director.id, type='导演')) 
            else:
                new_director = Actor(name=director_name, gender=None, country=None)
                db.session.add(new_director)
                db.session.commit() # 这里不做这一步的话就不会给new_actor生成id，不知道为什么
                if relationship: # 如果是空的就不执行
                    db.session.delete(relationship) # 删除对应的记录
                relationship = Relation(movie_id=movie_id, actor_id=new_director.id, type='导演')
                db.session.add(relationship) 
        
        None_Actor = Actor.query.filter_by(name=None).all() # 查找是否没有增添
        for none_actor in None_Actor:
            # relation_movies = none_actor.relations
            relation_movies = Relation.query.filter_by(actor_id=none_actor.id).all()
            db.session.delete(none_actor) # 删除对应的记录
            for r in relation_movies:
                db.session.delete(r) # 删除对应的记录
                
        None_Actor = Actor.query.filter_by(name='None').all() # 查找是否没有增添
        for none_actor in None_Actor:
            # relation_movies = none_actor.relations
            relation_movies = Relation.query.filter_by(actor_id=none_actor.id).all()
            db.session.delete(none_actor) # 删除对应的记录
            for r in relation_movies:
                db.session.delete(r) # 删除对应的记录
        
        db.session.commit() # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index')) # 重定向回主页
    return render_template('edit.html', movie=movie, actors=actors, directors=directors) # 传入被编辑的电影记录

# 删除电影条目
@app.route('/movie/delete/<int:movie_id>', methods=['POST']) # 限定只接受 POST 请求
@login_required # 登录保护
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id) # 获取电影记录
    relation_movie = movie.relations
    db.session.delete(movie) # 删除对应的记录
    for relation in relation_movie:
        db.session.delete(relation) # Relation里也要删除对应记录
    db.session.commit() # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index')) # 重定向回主页

# 查询电影条目
@app.route('/search', methods=['GET'])
def search():
    # 根据搜索查询查询电影
    search_query = request.args.get('search_query', '')
    search_results = Movie.query.filter(Movie.title.ilike(f'%{search_query}%')).all()

    Relation_movie_actor = []
    Relation_movie_director = []
    Actors = []
    Directors = []
    
    for search_result in search_results:
        
        actors = [] # 该电影的主演，以列表形式储存
        directors = [] # 该电影的导演，以列表形式储存
        
        relation_movie_actor = Relation.query.filter_by(movie_id=search_result.id, type='主演').all() # 所有主演关系
        for relation in relation_movie_actor:
            actor = Actor.query.filter_by(id=relation.actor_id).first()
            if actor:
                actors.append(actor)
        
        relation_movie_director = Relation.query.filter_by(movie_id=search_result.id, type='导演').all() # 所有导演关系
        for relation in relation_movie_director:
            director = Actor.query.filter_by(id=relation.actor_id).first()
            if director:
                directors.append(director)
                
        Actors.append(actors)
        Directors.append(directors)
        Relation_movie_actor.append(relation_movie_actor)
        Relation_movie_director.append(relation_movie_director)
        
    Result = zip(search_results, Actors, Directors)
    return render_template('search.html', Result=Result)

# 分析电影票房
@app.route('/movie/analyse_movie/<int:movie_id>', methods=['Get', 'POST']) # 限定只接受 POST 请求
@login_required # 登录保护
def analyse_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id) # 获取电影记录
    box = movie.box
    if not box:
        flash("该电影没有票房记录")
        rank = None
    else:
        Box = []
        type = movie.type
        all_movies = Movie.query.filter_by(type=type).order_by(Movie.box).all()
        for other_movie in all_movies:
            if other_movie.box:
                Box.append((other_movie.id, other_movie.box))
        num = 0
        for i in range(len(Box)):
            num = num + 1
            if Box[i][0] == movie_id:
                break
        rank = num*100 / len(Box)
        rank = round(rank, 2) # 保留2位小数
        
    return render_template('analyse_movie.html', movie=movie, rank=rank)
        
        
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

# 编辑演员条目
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
    actor = Actor.query.get_or_404(actor_id) # 获取演员记录
    relation_actor = Relation.query.filter_by(actor_id=actor.id).all()
    db.session.delete(actor) # 删除对应的记录
    for relation in relation_actor:
        db.session.delete(relation) # Relation里也要删除对应记录
    db.session.commit() # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index')) # 重定向回主页

# 查询演员条目
@app.route('/search_actor', methods=['GET'])
def search_actor():
    # 根据搜索查询查询电影
    search_query = request.args.get('search_query', '')
    search_results = Actor.query.filter(Actor.name.ilike(f'%{search_query}%')).all()
    
    Relation_movie_actor = []
    Relation_movie_director = []
    Actors = []
    Directors = []
    
    for search_result in search_results:
        
        actors = [] # 主演过的电影，以列表形式储存
        directors = [] # 导演过的电影，以列表形式储存
        
        relation_movie_actor = Relation.query.filter_by(actor_id=search_result.id, type='主演').all() # 所有主演关系
        for relation in relation_movie_actor:
            actor = Movie.query.filter_by(id=relation.movie_id).first()
            if actor:
                actors.append(actor)
        
        relation_movie_director = Relation.query.filter_by(actor_id=search_result.id, type='导演').all() # 所有导演关系
        for relation in relation_movie_director:
            director = Movie.query.filter_by(id=relation.movie_id).first()
            if director:
                directors.append(director)
                
        Actors.append(actors)
        Directors.append(directors)
        Relation_movie_actor.append(relation_movie_actor)
        Relation_movie_director.append(relation_movie_director)
        
    Result = zip(search_results, Actors, Directors)
    
    return render_template('search_actor.html', Result=Result)

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









# analyse

import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei']  #解决中文显示乱码问题
plt.rcParams['axes.unicode_minus']=False
# from IPython import get_ipython
# get_ipython().run_line_magic('matplotlib', 'inline')

# 分类型箱线图
@app.route('/analyse')
def analyse():    
    movie_types = db.session.query(Movie.type).distinct().all() # 不同类型的电影
    box_plot_data = [] # 储存不同种类的电影的数据
    
    for movie_type in movie_types:  # movie_types是列表，里面每一个movie_type是元组，形式为('战争',)
        movie_type_box = [] # 该类型的电影的票房，列表形式储存
        movies = Movie.query.filter_by(type=movie_type[0])
        for movie in movies:
            if movie.box:  # 非空才录入
                movie_type_box.append(movie.box)
        box_plot_data.append(movie_type_box) # 一个元素是一个列表
    
    plt.figure(figsize=(12, 6))
    for i, (movie_type, movie_box) in enumerate(zip(movie_types, box_plot_data)):
        plt.boxplot(movie_box, positions=[i + 1], labels=[movie_type[0]])
    
    image_path = f'static/analyse_box_plot.png'  # 储存在static里
    plt.savefig(image_path)
    
    return render_template('analyse.html', image_path=image_path)


import sklearn.linear_model as LM 
import pandas as pd
#建立线性预测模型
@app.route('/movie/predict/<int:movie_id>', methods=['GET', 'POST'])
@login_required # 登录保护
def predict(movie_id):
    movie_predict = Movie.query.filter_by(id=movie_id).first()
    
    if movie_predict.box:
        flash("该电影已有票房记录")
    else:
        flash("该电影暂无票房记录")
    
    df=[]  # 储存被解释变量和解释变量
    movies = Movie.query.all()
    for movie in movies:
        if movie.box:
            data = [movie.box, movie.year, movie.country, movie.type,
                    len(Relation.query.filter_by(movie_id=movie.id, type='主演').all()), # 有几个主演
                    len(Relation.query.filter_by(movie_id=movie.id, type='导演').all())] # 有几个导演
            df.append(data)
    df = pd.DataFrame(df) # 转变为数据框
    df.columns = ['box', 'year', 'country', 'type', 'actors', 'directors'] # 重命名
    y = df['box']
    x = df[['year', 'country', 'type', 'actors', 'directors']]
    # 预测的x0
    x0 = pd.DataFrame([[movie_predict.year, movie_predict.country, movie_predict.type,
                        len(Relation.query.filter_by(movie_id=movie_id, type='主演').all()),
                        len(Relation.query.filter_by(movie_id=movie_id, type='导演').all())]], # 必须是[[]]不然会是6行1列
                      columns = ['year', 'country', 'type', 'actors', 'directors'])  # 设置列名
    
    X = x._append(x0, ignore_index=True)  # x0在最后一行
    X = X.join(pd.get_dummies(X['country'])) # 生成country的虚拟变量
    X = X.drop(X.columns[[-1]], axis=1) # 删除最后一列防止多重共线性
    X = X.join(pd.get_dummies(X['type'])) # 生成type的虚拟变量
    X = X.drop(X.columns[[-1]], axis=1) # 删除最后一列防止多重共线性
    X = X.drop(['country', 'type'], axis=1) # 删除原数据列
    
    x0 = pd.DataFrame(X.iloc[-1,:]).T  # 只要单行时需要转置，多行不需要
    x = pd.DataFrame(X.iloc[:-1,:])
    
    modelLR = LM.LinearRegression() # 线性回归
    modelLR.fit(x,y) 
    box_predict = modelLR.predict(x0)
    
    return render_template('predict.html', movie_predict=movie_predict, box_predict=box_predict)






