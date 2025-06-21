"""
Современный асинхронный CLI интерфейс для TradingView OpenAPI Generator.
"""

import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from loguru import logger

from .config import settings
from .core import Pipeline, PipelineError
from .api import TradingViewAPI, TradingViewAPIError

app = typer.Typer(
    name="tvgen",
    help="TradingView OpenAPI Generator - автоматизированный генератор OpenAPI 3.1.0 спецификаций",
    add_completion=True,
    rich_markup_mode="rich"
)
console = Console()

# Экспортируем публичные асинхронные функции для тестов
__all__ = [
    "fetch_data",
    "health",
    "generate",
    "test_specs",
    "validate",
    "clean",
    "main",
    "fetch_data_async",
    "health_check_async"
]


def setup_logging(verbose: bool = False) -> None:
    """Настройка логирования."""
    level = "DEBUG" if verbose else settings.log_level
    
    logger.remove()
    logger.add(
        "logs/tvgen.log",
        level=level,
        format=settings.log_format,
        rotation="10 MB",
        retention="7 days"
    )
    logger.add(
        lambda msg: console.print(msg, end=""),
        level=level,
        format=settings.log_format
    )


@app.command()
def info():
    """Показать информацию о проекте и конфигурации."""
    table = Table(title="TradingView OpenAPI Generator Info")
    table.add_column("Параметр", style="cyan")
    table.add_column("Значение", style="green")
    
    table.add_row("Версия", "1.0.54")
    table.add_row("API URL", settings.tradingview_base_url)
    table.add_row("Таймаут", f"{settings.request_timeout}s")
    table.add_row("Retry", f"{settings.max_retries} попыток")
    table.add_row("Rate Limit", f"{settings.requests_per_second} req/s")
    table.add_row("Результаты", settings.results_dir)
    table.add_row("Спецификации", settings.specs_dir)
    
    console.print(table)
    
    markets_table = Table(title="Поддерживаемые рынки")
    markets_table.add_column("Рынок", style="cyan")
    markets_table.add_column("Описание", style="green")
    markets_table.add_column("Эндпоинт", style="yellow")
    
    for market_name, config in settings.markets.items():
        markets_table.add_row(
            market_name,
            config['description'],
            config['endpoint']
        )
    
    console.print(markets_table)


@app.command()
def fetch_data(
    markets: Optional[List[str]] = typer.Option(
        None, 
        "--market", "-m", 
        help="Конкретные рынки для обработки (например: us_stocks,crypto_coins)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    force: bool = typer.Option(False, "--force", "-f", help="Принудительная перезапись данных")
) -> None:
    """Сбор данных с TradingView API."""
    setup_logging(verbose)
    
    async def _fetch_data() -> None:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("🔄 Сбор данных с TradingView API...", total=None)
                
                pipeline = Pipeline()
                
                if markets:
                    # Обработка конкретных рынков
                    for market in markets:
                        if market not in settings.markets:
                            console.print(f"[red]❌ Неизвестный рынок: {market}[/red]")
                            raise typer.Exit(1)
                    
                    progress.update(task, description=f"📊 Обработка {len(markets)} рынков...")
                    
                    for market in markets:
                        market_config = settings.markets[market]
                        progress.update(task, description=f"📊 Обработка рынка: {market}")
                        
                        market_data = await pipeline.fetch_market_data(market, market_config)
                        pipeline.save_market_data(market_data)
                        
                        console.print(f"✅ [green]Рынок {market} обработан[/green]")
                else:
                    # Обработка всех рынков
                    progress.update(task, description="📊 Обработка всех рынков...")
                    await pipeline.run()
                
                progress.update(task, description="✅ Сбор данных завершен успешно!")
            
            console.print(Panel.fit("✅ Сбор данных завершен успешно!", style="green"))
            
        except TradingViewAPIError as e:
            logger.error(f"API ошибка: {e}")
            console.print(f"[red]❌ API ошибка: {e}[/red]")
            raise typer.Exit(1)
        except PipelineError as e:
            logger.error(f"Ошибка пайплайна: {e}")
            console.print(f"[red]❌ Ошибка пайплайна: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            console.print(f"[red]❌ Неожиданная ошибка: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_fetch_data())


@app.command()
def test_specs(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод")
):
    """Тестирование спецификаций."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🧪 Тестирование спецификаций...", total=None)
            
            # Импорт здесь для избежания циклических зависимостей
            from test_specifications import main as test_main
            test_main()
            
            progress.update(task, description="✅ Тестирование завершено успешно!")
        
        console.print(Panel.fit("✅ Тестирование завершено успешно!", style="green"))
        
    except Exception as e:
        console.print(f"[red]❌ Ошибка при тестировании: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate(
    output: Optional[str] = typer.Option(
        None, 
        "--output", "-o", 
        help="Путь для сохранения OpenAPI спецификации"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод")
):
    """Генерация OpenAPI спецификаций."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("📝 Генерация OpenAPI спецификаций...", total=None)
            
            # Импорт здесь для избежания циклических зависимостей
            from generate_openapi import main as gen_main
            gen_main()
            
            progress.update(task, description="✅ Генерация завершена успешно!")
        
        console.print(Panel.fit("✅ Генерация завершена успешно!", style="green"))
        
    except Exception as e:
        console.print(f"[red]❌ Ошибка при генерации: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate():
    """Валидация конфигурации и зависимостей."""
    console.print(Panel.fit("🔍 Валидация конфигурации...", style="blue"))
    
    # Проверка директорий
    results_dir = Path(settings.results_dir)
    specs_dir = Path(settings.specs_dir)
    
    table = Table(title="Результаты валидации")
    table.add_column("Проверка", style="cyan")
    table.add_column("Статус", style="green")
    table.add_column("Детали", style="yellow")
    
    # Проверка директорий
    if results_dir.exists():
        table.add_row("Директория результатов", "✅", str(results_dir))
    else:
        table.add_row("Директория результатов", "⚠️", f"Создастся автоматически: {results_dir}")
    
    if specs_dir.exists():
        table.add_row("Директория спецификаций", "✅", str(specs_dir))
    else:
        table.add_row("Директория спецификаций", "⚠️", f"Создастся автоматически: {specs_dir}")
    
    # Проверка рынков
    table.add_row("Конфигурация рынков", "✅", f"{len(settings.markets)} рынков")
    
    # Проверка API настроек
    table.add_row("API URL", "✅", settings.tradingview_base_url)
    table.add_row("Таймаут", "✅", f"{settings.request_timeout}s")
    table.add_row("Rate Limit", "✅", f"{settings.requests_per_second} req/s")
    
    console.print(table)


@app.command()
def health():
    """Проверка здоровья API и системы."""
    async def _health_check():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("🏥 Проверка здоровья системы...", total=None)
                
                api = TradingViewAPI()
                async with api:
                    health_status = await api.health_check()
                
                pipeline = Pipeline()
                pipeline_health = await pipeline.health_check()
                
                progress.update(task, description="✅ Проверка завершена!")
            
            # Выводим результаты
            table = Table(title="Статус здоровья системы")
            table.add_column("Компонент", style="cyan")
            table.add_column("Статус", style="green")
            table.add_column("Детали", style="yellow")
            
            table.add_row("API", health_status["status"], str(health_status["endpoints"]))
            table.add_row("Pipeline", pipeline_health["pipeline"], "")
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка при проверке здоровья: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_health_check())


@app.command()
def clean(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Подтвердить без запроса")
):
    """Очистка временных файлов и результатов."""
    results_dir = Path(settings.results_dir)
    specs_dir = Path(settings.specs_dir)
    logs_dir = Path("logs")
    
    files_to_remove = []
    
    if results_dir.exists():
        files_to_remove.extend(list(results_dir.glob("*")))
    
    if specs_dir.exists():
        files_to_remove.extend(list(specs_dir.glob("*.json")))
    
    if logs_dir.exists():
        files_to_remove.extend(list(logs_dir.glob("*.log")))
    
    if not files_to_remove:
        console.print("✨ Нет файлов для очистки")
        return
    
    console.print(f"🗑️ Найдено {len(files_to_remove)} файлов для удаления:")
    for file in files_to_remove[:10]:  # Показываем первые 10
        console.print(f"  - {file}")
    
    if len(files_to_remove) > 10:
        console.print(f"  ... и еще {len(files_to_remove) - 10} файлов")
    
    if not confirm:
        confirm = Confirm.ask("Продолжить удаление?")
    
    if confirm:
        for file in files_to_remove:
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    import shutil
                    shutil.rmtree(file)
            except Exception as e:
                console.print(f"⚠️ Не удалось удалить {file}: {e}")
        
        console.print("✅ Очистка завершена")
    else:
        console.print("❌ Очистка отменена")


def main() -> None:
    """Основная функция CLI."""
    app()


async def fetch_data_async(markets=None, verbose=False, force=False):
    """Асинхронная версия fetch_data для тестов и внутреннего использования."""
    setup_logging(verbose)
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🔄 Сбор данных с TradingView API...", total=None)
            pipeline = Pipeline()
            if markets:
                for market in markets:
                    if market not in settings.markets:
                        console.print(f"[red]❌ Неизвестный рынок: {market}[/red]")
                        raise typer.Exit(1)
                progress.update(task, description=f"📊 Обработка {len(markets)} рынков...")
                for market in markets:
                    market_config = settings.markets[market]
                    progress.update(task, description=f"📊 Обработка рынка: {market}")
                    market_data = await pipeline.fetch_market_data(market, market_config)
                    pipeline.save_market_data(market_data)
                    console.print(f"✅ [green]Рынок {market} обработан[/green]")
            else:
                progress.update(task, description="📊 Обработка всех рынков...")
                await pipeline.run()
            progress.update(task, description="✅ Сбор данных завершен успешно!")
        console.print(Panel.fit("✅ Сбор данных завершен успешно!", style="green"))
    except TradingViewAPIError as e:
        logger.error(f"API ошибка: {e}")
        console.print(f"[red]❌ API ошибка: {e}[/red]")
        raise typer.Exit(1)
    except PipelineError as e:
        logger.error(f"Ошибка пайплайна: {e}")
        console.print(f"[red]❌ Ошибка пайплайна: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        console.print(f"[red]❌ Неожиданная ошибка: {e}[/red]")
        raise typer.Exit(1)


async def health_check_async():
    """Асинхронная версия health_check для тестов и внутреннего использования."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🏥 Проверка здоровья системы...", total=None)
            api = TradingViewAPI()
            async with api:
                health_status = await api.health_check()
            pipeline = Pipeline()
            pipeline_health = await pipeline.health_check()
            progress.update(task, description="✅ Проверка завершена!")
        table = Table(title="Статус здоровья системы")
        table.add_column("Компонент", style="cyan")
        table.add_column("Статус", style="green")
        table.add_column("Детали", style="yellow")
        table.add_row("API", health_status["status"], str(health_status["endpoints"]))
        table.add_row("Pipeline", pipeline_health["pipeline"], "")
        console.print(table)
    except Exception as e:
        console.print(f"[red]❌ Ошибка при проверке здоровья: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    main() 