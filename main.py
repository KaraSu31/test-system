#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import random
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Tuple
from pathlib import Path


class TestQuestion:
    def __init__(self, text: str, correct_answer: str, all_answers: List[str]):
        self.text = text
        self.correct_answer = correct_answer
        self.all_answers = all_answers

    def __repr__(self):
        return f"Question: {self.text[:50]}..."


class DocxReader:
    """Чтение текста из .docx файлов"""

    @staticmethod
    def read_docx(filepath: str) -> str:
        """Извлекает текст из .docx файла"""
        try:
            with zipfile.ZipFile(filepath, 'r') as docx_zip:
                # Читаем основной документ
                with docx_zip.open('word/document.xml') as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()

                    # Пространства имен Word
                    namespaces = {
                        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                    }

                    # Извлекаем весь текст из параграфов
                    paragraphs = root.findall('.//w:p', namespaces)
                    text_content = []

                    for para in paragraphs:
                        texts = para.findall('.//w:t', namespaces)
                        para_text = ''.join([t.text for t in texts if t.text])
                        if para_text:
                            text_content.append(para_text)

                    return '\n'.join(text_content)
        except Exception as e:
            print(f"Ошибка при чтении .docx файла: {e}")
            return ""


class TestParser:
    """Парсер тестов из формата с #$ и # для ответов"""

    @staticmethod
    def parse_from_file(filepath: str) -> List[TestQuestion]:
        """Разбирает файл с тестами и возвращает список вопросов"""
        try:
            # Проверяем, существует ли файл
            if not os.path.isfile(filepath):
                print(f"Ошибка: '{filepath}' не является файлом или не существует!")
                return []

            # Определяем тип файла
            file_ext = os.path.splitext(filepath)[1].lower()
            content = ""

            if file_ext == '.docx':
                print("Обнаружен .docx файл, извлекаем текст...")
                content = DocxReader.read_docx(filepath)
                if not content:
                    print("Не удалось извлечь текст из .docx файла!")
                    return []
            else:
                # Для текстовых файлов пробуем разные кодировки
                encodings = ['utf-8', 'windows-1251', 'cp1251', 'latin-1']

                for encoding in encodings:
                    try:
                        with open(filepath, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    print("Ошибка: не удалось определить кодировку файла!")
                    return []

            return TestParser.parse(content)

        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return []

    @staticmethod
    def parse(text: str) -> List[TestQuestion]:
        """Разбирает текст теста и возвращает список вопросов"""
        questions = []

        # Разделяем текст на блоки вопросов (по символу @)
        blocks = re.split(r'@', text)

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split('\n')
            if not lines:
                continue

            question_text = ""
            answers = []
            correct_answer = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Если строка начинается с #$, это правильный ответ
                if line.startswith('#$'):
                    answer = line[2:].strip()
                    answers.append(answer)
                    correct_answer = answer
                # Если строка начинается с #, это обычный ответ
                elif line.startswith('#'):
                    answer = line[1:].strip()
                    answers.append(answer)
                # Иначе это текст вопроса
                else:
                    if question_text:
                        question_text += " " + line
                    else:
                        question_text = line

            # Если нашли вопрос с ответами
            if question_text and answers and correct_answer:
                questions.append(TestQuestion(question_text, correct_answer, answers))

        return questions


class FileSelector:
    """Выбор файла с тестами"""

    @staticmethod
    def select_file() -> str:
        """Интерактивный выбор файла"""
        while True:
            print("\n" + "=" * 70)
            print("                     ВЫБОР ФАЙЛА С ТЕСТАМИ")
            print("=" * 70)
            print("\nВарианты ввода:")
            print("  1. Ввести полный путь к файлу")
            print("  2. Выбрать файл из папки")
            print("  3. Выход")

            choice = input("\nВыберите вариант (1-3): ").strip()

            if choice == '1':
                filepath = input("\nВведите полный путь к файлу: ").strip()
                filepath = filepath.strip('"').strip("'")
                if os.path.isfile(filepath):
                    return filepath
                else:
                    print(f"\n❌ Файл не найден: {filepath}")
                    input("Нажмите Enter для продолжения...")

            elif choice == '2':
                folder = input("\nВведите путь к папке (или Enter для текущей): ").strip()
                folder = folder.strip('"').strip("'")

                if not folder:
                    folder = os.getcwd()

                if not os.path.isdir(folder):
                    print(f"\n❌ Папка не найдена: {folder}")
                    input("Нажмите Enter для продолжения...")
                    continue

                files = FileSelector.find_test_files(folder)

                if not files:
                    print(f"\n❌ В папке '{folder}' не найдено подходящих файлов")
                    input("Нажмите Enter для продолжения...")
                    continue

                print(f"\n📁 Найдено файлов: {len(files)}")
                print("-" * 70)
                for i, file in enumerate(files, 1):
                    size = os.path.getsize(os.path.join(folder, file)) / 1024
                    print(f"  {i}. {file} ({size:.1f} KB)")

                print(f"  {len(files) + 1}. Ввести путь вручную")
                print(f"  {len(files) + 2}. Назад")

                while True:
                    try:
                        file_choice = input(f"\nВыберите файл (1-{len(files) + 2}): ").strip()
                        file_num = int(file_choice)

                        if 1 <= file_num <= len(files):
                            return os.path.join(folder, files[file_num - 1])
                        elif file_num == len(files) + 1:
                            break
                        elif file_num == len(files) + 2:
                            break
                        else:
                            print(f"Введите число от 1 до {len(files) + 2}")
                    except ValueError:
                        print("Введите число")

            elif choice == '3':
                return None
            else:
                print("Неверный выбор. Попробуйте снова.")

    @staticmethod
    def find_test_files(folder: str) -> List[str]:
        """Находит файлы, которые могут содержать тесты"""
        test_extensions = ['.txt', '.docx', '.doc', '.rtf', '.md']
        test_files = []

        try:
            for file in os.listdir(folder):
                file_lower = file.lower()
                if any(file_lower.endswith(ext) for ext in test_extensions):
                    test_files.append(file)
        except PermissionError:
            print(f"Нет доступа к папке: {folder}")

        return sorted(test_files)


class TestTaker:
    """Проведение тестирования"""

    def __init__(self, questions: List[TestQuestion]):
        self.all_questions = questions
        self.current_questions = []
        self.results = []
        self.score = 0

    def select_random_questions(self, count: int) -> bool:
        """Выбирает случайные вопросы для тестирования"""
        if count > len(self.all_questions):
            print(f"\n⚠ Предупреждение: запрошено {count} вопросов, но доступно только {len(self.all_questions)}")
            print(f"Будут использованы все доступные вопросы ({len(self.all_questions)})\n")
            self.current_questions = self.all_questions.copy()
            return True
        elif count <= 0:
            print("Ошибка: количество вопросов должно быть положительным!")
            return False
        else:
            self.current_questions = random.sample(self.all_questions, count)
            return True

    def run(self):
        """Запуск тестирования"""
        if not self.current_questions:
            print("Нет вопросов для тестирования!")
            return

        print("\n" + "=" * 70)
        print("                     КОНСОЛЬНОЕ ТЕСТИРОВАНИЕ")
        print("=" * 70)
        print(f"Всего вопросов в тесте: {len(self.current_questions)}")
        print(f"Всего доступно вопросов: {len(self.all_questions)}")
        print("\nПравила:")
        print("- Для выбора ответа введите его номер (1-4)")
        print("- Для выхода нажмите Ctrl+C")
        print("=" * 70 + "\n")

        input("Нажмите Enter, чтобы начать тест...")

        for i, question in enumerate(self.current_questions, 1):
            shuffled_answers = question.all_answers.copy()
            random.shuffle(shuffled_answers)
            correct_in_shuffled = question.correct_answer

            print(f"\n{'█' * 60}")
            print(f"Вопрос {i}/{len(self.current_questions)}:")
            print(f"\n{question.text}")
            print()

            for j, answer in enumerate(shuffled_answers, 1):
                print(f"  {j}. {answer}")

            print()

            while True:
                try:
                    choice = input("Ваш ответ (1-4): ").strip()
                    if choice.lower() == 'q':
                        raise KeyboardInterrupt

                    choice_num = int(choice)
                    if 1 <= choice_num <= len(shuffled_answers):
                        break
                    else:
                        print(f"Пожалуйста, введите число от 1 до {len(shuffled_answers)}")
                except ValueError:
                    print("Пожалуйста, введите число")
                except KeyboardInterrupt:
                    self._show_exit()
                    return

            selected_answer = shuffled_answers[choice_num - 1]
            is_correct = selected_answer == correct_in_shuffled

            if is_correct:
                print("\n✅ ПРАВИЛЬНО!")
                self.score += 1
                self.results.append((question, selected_answer, correct_in_shuffled, True))
            else:
                print(f"\n❌ НЕПРАВИЛЬНО!")
                print(f"Правильный ответ: {correct_in_shuffled}")
                self.results.append((question, selected_answer, correct_in_shuffled, False))

            print()
            if i < len(self.current_questions):
                input("Нажмите Enter для следующего вопроса...")

        self._show_results()

    def _show_results(self):
        """Показывает результаты тестирования"""
        print("\n" + "=" * 70)
        print("                       РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("=" * 70)
        print(f"\n📊 Статистика:")
        print(f"   ✅ Правильных ответов: {self.score} из {len(self.current_questions)}")
        print(f"   ❌ Неправильных ответов: {len(self.current_questions) - self.score}")
        print(f"   📈 Процент выполнения: {self.score / len(self.current_questions) * 100:.1f}%")

        percentage = self.score / len(self.current_questions) * 100
        print(f"\n🎓 Оценка:")
        if percentage >= 90:
            print("   Отлично (5) - Вы превосходно знаете материал!")
        elif percentage >= 75:
            print("   Хорошо (4) - Неплохой результат!")
        elif percentage >= 60:
            print("   Удовлетворительно (3) - Есть над чем поработать")
        else:
            print("   Неудовлетворительно (2) - Рекомендуется повторить материал")

        print("\n" + "=" * 70)

        wrong_answers = [r for r in self.results if not r[3]]
        if wrong_answers:
            print(f"\n📝 РАЗБОР ОШИБОК ({len(wrong_answers)} вопросов):")
            print("-" * 70)
            for i, (q, selected, correct, _) in enumerate(wrong_answers, 1):
                print(f"\n❌ Вопрос {i}:")
                print(f"   {q.text}")
                print(f"   Ваш ответ: {selected}")
                print(f"   Правильный ответ: {correct}")
        else:
            print("\n🎉 Поздравляем! Все ответы правильные! 🎉")

    def _show_exit(self):
        """Показывает сообщение при выходе"""
        print("\n\n⚠ Тестирование прервано пользователем.")
        if self.results:
            print(f"На момент выхода правильных ответов: {self.score} из {len(self.results)}")


def main():
    """Главная функция"""
    print("=" * 70)
    print("              СИСТЕМА ТЕСТИРОВАНИЯ")
    print("=" * 70)
    print("\nДанная программа читает тесты из файла и проводит")
    print("случайную выборку вопросов для тестирования.")
    print("Формат файла: @ - вопрос, #$ - правильный ответ")
    print("=" * 70)

    # Выбираем файл
    selector = FileSelector()
    filepath = selector.select_file()

    if not filepath:
        print("\nВыход из программы.")
        return

    print(f"\n📖 Чтение файла: {filepath}")

    # Парсим тесты
    parser = TestParser()
    questions = parser.parse_from_file(filepath)

    if not questions:
        print("\n❌ Ошибка: не удалось найти вопросы в указанном формате!")
        print("Убедитесь, что в файле вопросы отмечены символом @, а правильные ответы — #$")
        return

    print(f"✅ Найдено вопросов: {len(questions)}")

    # Выбор количества вопросов
    print(f"\n📋 Доступно {len(questions)} вопросов.")
    while True:
        try:
            count_input = input(f"Сколько вопросов включить в тест (1-{len(questions)}): ").strip()
            num_questions = int(count_input)
            if 1 <= num_questions <= len(questions):
                break
            else:
                print(f"Пожалуйста, введите число от 1 до {len(questions)}")
        except ValueError:
            print("Пожалуйста, введите целое число")

    # Создаём тест
    taker = TestTaker(questions)

    if not taker.select_random_questions(num_questions):
        return

    # Запускаем тестирование
    taker.run()

    print("\n✨ Спасибо за прохождение теста! ✨")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма завершена пользователем.")
        sys.exit(0)