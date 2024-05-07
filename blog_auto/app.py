import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QCheckBox


class BlogDownloader(QWidget):
    def __init__(self):
        super().__init__()

        self.hexo_dir = None
        self.category_dir = None
        self.download_dir = None
        self.has_git_attr = False

        self.hexo_label = QLabel('Hexo博客目录: 未选择')
        self.category_label = QLabel('分类图片目录: 未选择')
        self.download_label = QLabel('博客内含图片下载目录: 未选择')

        self.git_attr_checkbox = QCheckBox('是否有git属性', self)
        self.git_attr_checkbox.stateChanged.connect(self.git_attr_checkbox_changed)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        hexo_button = QPushButton('选择目录', self)
        hexo_button.clicked.connect(self.choose_hexo_directory)

        category_button = QPushButton('选择目录', self)
        category_button.clicked.connect(self.choose_category_directory)

        download_button = QPushButton('选择目录', self)
        download_button.clicked.connect(self.choose_download_directory)

        execute_button = QPushButton('执行', self)
        execute_button.clicked.connect(self.execute)

        layout.addWidget(self.hexo_label)
        layout.addWidget(hexo_button)
        layout.addWidget(self.category_label)
        layout.addWidget(category_button)
        layout.addWidget(self.download_label)
        layout.addWidget(download_button)
        layout.addWidget(self.git_attr_checkbox)
        layout.addWidget(execute_button)

        self.setLayout(layout)
        self.setWindowTitle('Blog Downloader')

    def choose_hexo_directory(self):
        self.hexo_dir = self.choose_directory()
        if self.hexo_dir:
            self.hexo_label.setText(f'Hexo博客目录: {self.hexo_dir}')

    def choose_category_directory(self):
        self.category_dir = self.choose_directory()
        if self.category_dir:
            self.category_label.setText(f'分类图片目录: {self.category_dir}')

    def choose_download_directory(self):
        self.download_dir = self.choose_directory()
        if self.download_dir:
            self.download_label.setText(f'博客内含图片下载目录: {self.download_dir}')

    def git_attr_checkbox_changed(self):
        self.has_git_attr = self.git_attr_checkbox.isChecked()

    def choose_directory(self):
        directory = QFileDialog.getExistingDirectory(self, '选择目录')
        return directory

    def execute(self):
        if self.hexo_dir is None or self.category_dir is None or self.download_dir is None:
            print('请完成选择对应目录')
        else:
            print('执行操作：Hexo博客目录 - {}, 分类图片目录 - {}, 下载目录 - {}'.format(
                self.hexo_dir, self.category_dir, self.download_dir))
            print('是否有git属性: {}'.format(self.has_git_attr))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BlogDownloader()
    window.show()
    sys.exit(app.exec_())
