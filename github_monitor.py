"""
Мониторинг GitHub репозитория SS14
Отслеживает статус билда, новые коммиты и релизы
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from github import Github, GithubException
from github.Repository import Repository
from config import GITHUB_TOKEN, GITHUB_REPO


class GitHubMonitor:
    """Класс для мониторинга GitHub репозитория"""
    
    def __init__(self):
        """Инициализирует подключение к GitHub"""
        try:
            if not GITHUB_TOKEN:
                print("⚠️ GITHUB_TOKEN не установлен. GitHub функции отключены.")
                self.github = None
                self.repo = None
                return
            
            self.github = Github(GITHUB_TOKEN)
            self.repo: Repository = self.github.get_repo(GITHUB_REPO)
            print(f"✅ GitHub подключен к {GITHUB_REPO}")
            
            # Кэш для отслеживания новых события
            self.last_commit_sha = None
            self.last_build_status = None
            
        except GithubException as e:
            print(f"❌ Ошибка подключения к GitHub: {e}")
            self.github = None
            self.repo = None
    
    def is_connected(self) -> bool:
        """Проверяет, подключены ли к GitHub"""
        return self.repo is not None
    
    def get_latest_commits(self, count: int = 5) -> Optional[List[Dict]]:
        """
        Получает последние коммиты
        
        Args:
            count: Количество коммитов для получения
            
        Returns:
            Список с информацией о коммитах или None при ошибке
        """
        if not self.is_connected():
            return None
        
        try:
            commits = []
            for commit in self.repo.get_commits()[:count]:
                commits.append({
                    "sha": commit.sha[:7],  # Первые 7 символов хеша
                    "author": commit.commit.author.name,
                    "message": commit.commit.message.split('\n')[0],  # Первая строка сообщения
                    "date": commit.commit.author.date,
                    "url": commit.html_url
                })
            
            return commits
            
        except Exception as e:
            print(f"❌ Ошибка получения коммитов: {e}")
            return None
    
    def get_build_status(self) -> Optional[Dict]:
        """
        Получает статус последнего билда (через проверку последнего коммита)
        
        Returns:
            Информация о статусе билда или None при ошибке
        """
        if not self.is_connected():
            return None
        
        try:
            latest_commit = self.repo.get_commits()[0]
            
            # Получаем статусы для коммита
            statuses = latest_commit.get_statuses()
            
            if statuses.totalCount == 0:
                return {
                    "commit": latest_commit.sha[:7],
                    "status": "unknown",
                    "description": "Статус билда еще не доступен",
                    "message": latest_commit.commit.message.split('\n')[0]
                }
            
            # Берем самый последний статус
            latest_status = statuses[0]
            
            return {
                "commit": latest_commit.sha[:7],
                "status": latest_status.state,  # success, pending, failure, error
                "description": latest_status.description,
                "context": latest_status.context,
                "message": latest_commit.commit.message.split('\n')[0],
                "url": latest_status.target_url,
                "updated": latest_status.updated_at
            }
            
        except Exception as e:
            print(f"⚠️ Ошибка получения статуса билда: {e}")
            return None
    
    def get_repo_info(self) -> Optional[Dict]:
        """
        Получает основную информацию о репозитории
        
        Returns:
            Информация о репозитории
        """
        if not self.is_connected():
            return None
        
        try:
            return {
                "name": self.repo.name,
                "url": self.repo.html_url,
                "description": self.repo.description,
                "stars": self.repo.stargazers_count,
                "forks": self.repo.forks_count,
                "watchers": self.repo.watchers_count,
                "language": self.repo.language,
                "updated": self.repo.updated_at,
                "is_fork": self.repo.fork,
                "topics": self.repo.topics
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения информации о репо: {e}")
            return None
    
    def get_latest_releases(self, count: int = 3) -> Optional[List[Dict]]:
        """
        Получает последние релизы
        
        Args:
            count: Количество релизов для получения
            
        Returns:
            Список информации о релизах
        """
        if not self.is_connected():
            return None
        
        try:
            releases = []
            for release in self.repo.get_releases()[:count]:
                releases.append({
                    "name": release.title,
                    "tag": release.tag_name,
                    "published": release.published_at,
                    "draft": release.draft,
                    "prerelease": release.prerelease,
                    "url": release.html_url,
                    "assets_count": len(release.assets)
                })
            
            return releases
            
        except Exception as e:
            print(f"❌ Ошибка получения релизов: {e}")
            return None
    
    def get_open_pulls(self, count: int = 5) -> Optional[List[Dict]]:
        """
        Получает открытые pull requests
        
        Args:
            count: Количество PR для получения
            
        Returns:
            Список информации о открытых PR
        """
        if not self.is_connected():
            return None
        
        try:
            prs = []
            for pr in self.repo.get_pulls(state='open')[:count]:
                prs.append({
                    "number": pr.number,
                    "title": pr.title,
                    "author": pr.user.login,
                    "created": pr.created_at,
                    "url": pr.html_url,
                    "comments": pr.comments,
                    "changed_files": pr.changed_files
                })
            
            return prs
            
        except Exception as e:
            print(f"❌ Ошибка получения PR: {e}")
            return None
    
    def format_build_status_message(self) -> Optional[str]:
        """Форматирует красивое сообщение о статусе билда"""
        status_info = self.get_build_status()
        
        if not status_info:
            return "⚠️ Не удалось получить статус билда"
        
        status_emoji = {
            "success": "✅",
            "pending": "⏳",
            "failure": "❌",
            "error": "⚠️",
            "unknown": "❓"
        }.get(status_info.get("status", "unknown"), "❓")
        
        message = f"""{status_emoji} **Статус билда SS14**
        
**Коммит:** `{status_info['commit']}`
**Статус:** {status_info['description']}
**Сообщение:** {status_info['message']}"""
        
        if status_info.get('url'):
            message += f"\n**Подробнее:** {status_info['url']}"
        
        return message
    
    def format_latest_commits_message(self) -> Optional[str]:
        """Форматирует красивое сообщение с последними коммитами"""
        commits = self.get_latest_commits(3)
        
        if not commits:
            return "⚠️ Не удалось получить коммиты"
        
        message = "📝 **Последние коммиты SS14:**\n\n"
        
        for commit in commits:
            message += f"• `{commit['sha']}` - {commit['author']}\n"
            message += f"  {commit['message']}\n"
            message += f"  🕐 {commit['date'].strftime('%d.%m.%Y %H:%M')}\n\n"
        
        return message.strip()
