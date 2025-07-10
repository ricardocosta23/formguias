import uuid
import logging
import json
import os
from datetime import datetime

class FormGenerator:
    """Dynamic form generation utilities"""

    def __init__(self):
        self.forms_folder = "Forms"
        # Create Forms folder if it doesn't exist
        os.makedirs(self.forms_folder, exist_ok=True)

    def generate_form(self, form_data):
        """Generate a unique form ID and store form data"""
        form_id = str(uuid.uuid4())

        # Enrich form data with metadata
        form_data.update({
            "id": form_id,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        })

        # Save form data to file
        form_file_path = os.path.join(self.forms_folder, f"{form_id}.json")
        try:
            with open(form_file_path, 'w', encoding='utf-8') as f:
                json.dump(form_data, f, indent=2, ensure_ascii=False)
            logging.info(f"Generated and saved form {form_id} for type {form_data.get('type')}")
        except Exception as e:
            logging.error(f"Error saving form {form_id}: {str(e)}")
            raise

        return form_id

    def get_form_data(self, form_id):
        """Retrieve form data by ID"""
        form_file_path = os.path.join(self.forms_folder, f"{form_id}.json")
        try:
            if os.path.exists(form_file_path):
                with open(form_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logging.error(f"Error loading form {form_id}: {str(e)}")
            return None

    def generate_html_form(self, form_data):
        """Generate HTML form from configuration"""
        form_html = []

        # Form header
        form_html.append(f'<h1 class="survey-title">{form_data.get("title", "Formulário")}</h1>')
        form_html.append(f'<p class="survey-subtitle">{form_data.get("subtitle", "")}</p>')

        # Generate header fields section if available
        if form_data.get("header_data"):
            header_html = self._generate_header_section(form_data.get("header_data"))
            form_html.append(header_html)

        # Generate questions
        for question in form_data.get("questions", []):
            question_id = question.get("id", str(uuid.uuid4()))
            question_type = question.get("type", "text")
            required = question.get("required", False)
            is_conditional = question.get("is_conditional", False)

            if question_type == "text":
                question_html = self._generate_text_question(question_id, question, required)
            elif question_type == "longtext":
                question_html = self._generate_textarea_question(question_id, question, required)
            elif question_type == "dropdown":
                question_html = self._generate_dropdown_question(question_id, question, required)
            elif question_type == "yesno":
                question_html = self._generate_yesno_question(question_id, question, required)
            elif question_type == "rating":
                question_html = self._generate_rating_question(question_id, question, required)
            elif question_type == "monday_column":
                question_html = self._generate_monday_column_question(question_id, question, required)
            else:
                question_html = self._generate_text_question(question_id, question, required)

            # Don't wrap conditional questions here since it's handled in the template
            # Just add the question HTML as is

            form_html.append(question_html)

        return "\n".join(form_html)

    def _generate_header_section(self, header_data):
        """Generate header section with Monday.com data and icons"""
        header_html = f"""
        <div class="header-section">
            <h3><i data-feather="info"></i> Informações da Viagem</h3>
            <div class="header-data">
        """

        # Display in specific order with icons: Viagem, Destino, Data, Cliente
        header_config = [
            {'key': 'Viagem', 'icon': 'map-pin'},
            {'key': 'Destino', 'icon': 'navigation'},
            {'key': 'Data', 'icon': 'calendar'},
            {'key': 'Cliente', 'icon': 'user'}
        ]

        for item in header_config:
            key = item['key']
            icon = item['icon']
            if key in header_data and header_data[key]:
                header_html += f"""
                    <div class="header-item">
                        <i data-feather="{icon}" class="header-icon"></i>
                        <strong>{key}:</strong> <span class="header-value">{header_data[key]}</span>
                    </div>
                """

        header_html += """
            </div>
        </div>
        """

        return header_html

    def _generate_text_question(self, question_id, question, required):
        """Generate text input question HTML"""
        question_text = question.get("text", "")
        placeholder = question.get("placeholder", "")
        required_attr = 'required' if required else ''

        return f"""
        <div class="question-section">
            <label class="feedback-label" for="{question_id}">
                <i data-feather="edit-3"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <input type="text" 
                   id="{question_id}" 
                   name="{question_id}" 
                   class="form-control" 
                   placeholder="{placeholder}"
                   {required_attr}
                   style="padding: var(--spacing-md); border: 2px solid hsl(var(--gray-300)); border-radius: var(--radius-lg);">
        </div>
        """

    def _generate_textarea_question(self, question_id, question, required):
        """Generate textarea question HTML"""
        question_text = question.get("text", "")
        placeholder = question.get("placeholder", "")
        required_attr = 'required' if required else ''

        return f"""
        <div class="question-section">
            <label class="feedback-label" for="{question_id}">
                <i data-feather="message-square"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <textarea id="{question_id}" 
                      name="{question_id}" 
                      class="form-control" 
                      rows="4" 
                      placeholder="{placeholder}"
                      {required_attr}
                      style="padding: var(--spacing-md); border: 2px solid hsl(var(--gray-300)); border-radius: var(--radius-lg);"></textarea>
        </div>
        """

    def _generate_select_question(self, question_id, question, required):
        """Generate select dropdown question HTML"""
        question_text = question.get("text", "")
        options = question.get("options", [])
        required_attr = 'required' if required else ''

        options_html = '<option value="">Selecione uma opção</option>'
        for option in options:
            if isinstance(option, dict):
                value = option.get("value", "")
                label = option.get("label", "")
            else:
                value = label = str(option)

            options_html += f'<option value="{value}">{label}</option>'

        return f"""
        <div class="question-section">
            <label class="feedback-label" for="{question_id}">
                <i data-feather="list"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <select id="{question_id}" 
                    name="{question_id}" 
                    class="form-control" {required_attr}
                    style="padding: var(--spacing-md); border: 2px solid hsl(var(--gray-300)); border-radius: var(--radius-lg);">
                {options_html}
            </select>
        </div>
        """

    def _generate_radio_question(self, question_id, question, required):
        """Generate radio button question HTML"""
        question_text = question.get("text", "")
        options = question.get("options", [])
        required_attr = 'required' if required else ''

        options_html = ""
        for i, option in enumerate(options):
            if isinstance(option, dict):
                value = option.get("value", "")
                label = option.get("label", "")
            else:
                value = label = str(option)

            options_html += f"""
                <div class="form-check">
                    <input class="form-check-input" 
                           type="radio" 
                           name="{question_id}" 
                           id="{question_id}_{i}" 
                           value="{value}" 
                           {required_attr}>
                    <label class="form-check-label" for="{question_id}_{i}">
                        {label}
                    </label>
                </div>
            """

        return f"""
        <div class="question-section">
            <label class="feedback-label">
                <i data-feather="radio"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <div class="radio-group">
                {options_html}
            </div>
        </div>
        """

    def _generate_checkbox_question(self, question_id, question, required):
        """Generate checkbox question HTML"""
        question_text = question.get("text", "")
        options = question.get("options", [])
        required_attr = 'required' if required else ''

        options_html = ""
        for i, option in enumerate(options):
            if isinstance(option, dict):
                value = option.get("value", "")
                label = option.get("label", "")
            else:
                value = label = str(option)

            options_html += f"""
                <div class="form-check">
                    <input class="form-check-input" 
                           type="checkbox" 
                           name="{question_id}" 
                           id="{question_id}_{i}" 
                           value="{value}" 
                           {required_attr}>
                    <label class="form-check-label" for="{question_id}_{i}">
                        {label}
                    </label>
                </div>
            """

        return f"""
        <div class="question-section">
            <label class="feedback-label">
                <i data-feather="check-square"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <div class="checkbox-group">
                {options_html}
            </div>
        </div>
        """

    def _generate_monday_column_question(self, question_id, question, required):
        """Generate Monday column question HTML - displays data from Monday.com column as rating question"""
        source_column = question.get("source_column", "")
        column_value = question.get("column_value", "")

        # Debug logging
        logging.info(f"Monday column question - ID: {question_id}, Source: {source_column}, Value: '{column_value}'")

        # List of invalid/empty states that should hide the question
        invalid_values = [
            "Erro ao carregar dados", 
            "Dados não encontrados", 
            "Dados não disponíveis", 
            "Configuração incompleta",
            None,
            ""
        ]

        # If column value is empty, error, or None, don't show the question
        if not column_value or str(column_value).strip() == "" or column_value in invalid_values:
            logging.info(f"Skipping Monday column question {question_id} - empty or error value: '{column_value}'")
            return ""

        # Use column value as the question title (without bold styling)
        question_text = str(column_value).strip()
        required_attr = 'required' if required else ''

        rating_circles = ""
        for i in range(1, 11):
            rating_circles += f"""
                <div class="rating-circle" onclick="selectRating('{question_id}', {i})" data-value="{i}">
                    {i}
                </div>
            """

        return f"""
        <div class="question-section">
            <div class="hotel-rating">
                <label class="rating-label">{question_text}{' *' if required else ''}</label>
                <div class="rating-scale-small">
                    <div class="rating-numbers">
                        {rating_circles}
                    </div>
                    <input type="hidden" id="{question_id}_input" name="{question_id}" {required_attr}>
                </div>
            </div>
        </div>
        """

    def _generate_section_header(self, section_title):
        """Generate section header HTML"""
        return f"""
        <div class="form-section-header">
            <h3 class="section-title">
                <i data-feather="folder"></i>
                {section_title}
            </h3>
            <div class="section-divider"></div>
        </div>
        """

    def _generate_dropdown_question(self, question_id, question, required):
        """Generate dropdown question HTML"""
        question_text = question.get("text", "")
        dropdown_options = question.get("dropdown_options", "")
        required_attr = 'required' if required else ''

        options_html = '<option value="">Selecione uma opção</option>'
        if dropdown_options:
            options = dropdown_options.split(';')
            for option in options:
                option = option.strip()
                if option:
                    options_html += f'<option value="{option}">{option}</option>'

        return f"""
        <div class="question-section">
            <label class="feedback-label" for="{question_id}">
                <i data-feather="list"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <select id="{question_id}" 
                    name="{question_id}" 
                    class="form-control" {required_attr}
                    style="padding: var(--spacing-md); border: 2px solid hsl(var(--gray-300)); border-radius: var(--radius-lg);">
                {options_html}
            </select>
        </div>
        """

    def _generate_yesno_question(self, question_id, question, required):
        """Generate yes/no question HTML"""
        question_text = question.get("text", "")
        required_attr = 'required' if required else ''

        return f"""
        <div class="question-section">
            <label class="feedback-label">
                <i data-feather="help-circle"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <div class="radio-group">
                <div class="form-check">
                    <input class="form-check-input" 
                           type="radio" 
                           name="{question_id}" 
                           id="{question_id}_yes" 
                           value="yes" 
                           {required_attr}>
                    <label class="form-check-label" for="{question_id}_yes">
                        Sim
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" 
                           type="radio" 
                           name="{question_id}" 
                           id="{question_id}_no" 
                           value="no" 
                           {required_attr}>
                    <label class="form-check-label" for="{question_id}_no">
                        Não
                    </label>
                </div>
            </div>
        </div>
        """

    def _generate_rating_question(self, question_id, question, required):
        """Generate rating question HTML (1-10 scale)"""
        question_text = question.get("text", "")
        required_attr = 'required' if required else ''

        rating_circles = ""
        for i in range(1, 11):
            rating_circles += f"""
                <div class="rating-circle" onclick="selectRating('{question_id}', {i})" data-value="{i}">
                    {i}
                </div>
            """

        return f"""
        <div class="question-section">
            <label class="feedback-label">
                <i data-feather="star"></i>
                {question_text}
                {' *' if required else ''}
            </label>
            <div class="rating-container">
                {rating_circles}
            </div>
            <input type="hidden" id="{question_id}_input" name="{question_id}" {required_attr}>
            <style>
                .rating-container {{
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                    margin-top: 8px;
                }}
                .rating-circle {{
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    border: 2px solid hsl(var(--gray-300));
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    font-weight: 600;
                    transition: all 0.2s ease;
                    background: white;
                }}
                .rating-circle:hover {{
                    border-color: hsl(var(--primary-500));
                    background: hsl(var(--primary-50));
                }}
                .rating-circle.selected {{
                    background: hsl(var(--primary-500));
                    border-color: hsl(var(--primary-500));
                    color: white;
                }}
            </style>
        </div>
        """

    def validate_form_submission(self, form_data, submission_data):
        """Validate form submission against configuration"""
        errors = []

        for question in form_data.get("questions", []):
            question_id = question.get("id")
            required = question.get("required", False)

            if required and (question_id not in submission_data or not submission_data[question_id].strip()):
                question_text = question.get("text", f"Question {question_id}")
                errors.append(f"O campo '{question_text}' é obrigatório")

        return errors

    def list_all_forms(self):
        """List all saved forms with their metadata"""
        forms = []
        try:
            if os.path.exists(self.forms_folder):
                for filename in os.listdir(self.forms_folder):
                    if filename.endswith('.json'):
                        form_id = filename[:-5]  # Remove .json extension
                        form_data = self.get_form_data(form_id)
                        if form_data:
                            forms.append({
                                'id': form_id,
                                'title': form_data.get('title', 'Formulário sem título'),
                                'type': form_data.get('type', 'unknown'),
                                'created_at': form_data.get('created_at'),
                                'item_name': form_data.get('item_name', ''),
                                'webhook_data': form_data.get('webhook_data', {})
                            })
        except Exception as e:
            logging.error(f"Error listing forms: {str(e)}")

        # Sort by creation date (newest first)
        forms.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return forms

    def delete_form(self, form_id):
        """Delete a form by ID"""
        form_file_path = os.path.join(self.forms_folder, f"{form_id}.json")
        try:
            if os.path.exists(form_file_path):
                os.remove(form_file_path)
                logging.info(f"Deleted form {form_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting form {form_id}: {str(e)}")
            return False