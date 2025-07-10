import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
import json

# Import API modules
from api.formguias import formguias_bp
from api.formclientes import formclientes_bp  
from api.formfornecedores import formfornecedores_bp

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback-secret-key-for-development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Register blueprints
app.register_blueprint(formguias_bp)
app.register_blueprint(formclientes_bp)
app.register_blueprint(formfornecedores_bp)

@app.route('/')
def index():
    """Home page with navigation to admin interface"""
    return render_template('base.html')

@app.route('/admin')
def admin():
    """Admin interface for managing form configurations"""
    try:
        with open('setup/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        # Create default config if not exists
        config = {
            "guias": {
                "board_a": "",
                "board_b": "",
                "link_column": "",
                "questions": []
            },
            "clientes": {
                "board_a": "",
                "board_b": "",
                "link_column": "",
                "questions": []
            },
            "fornecedores": {
                "board_a": "",
                "board_b": "",
                "link_column": "",
                "questions": []
            }
        }
        # Save default config
        os.makedirs('setup', exist_ok=True)
        with open('setup/config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    return render_template('admin.html', config=config)

@app.route('/api/config', methods=['GET', 'POST'])
def config_api():
    """API endpoint for managing configurations"""
    if request.method == 'GET':
        try:
            with open('setup/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify(config)
        except FileNotFoundError:
            return jsonify({"error": "Configuration file not found"}), 404

    elif request.method == 'POST':
        try:
            config = request.get_json()
            os.makedirs('setup', exist_ok=True)
            with open('setup/config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return jsonify({"message": "Configuration saved successfully"})
        except Exception as e:
            app.logger.error(f"Error saving configuration: {str(e)}")
            return jsonify({"error": "Failed to save configuration"}), 500

@app.route('/api/forms', methods=['GET'])
def list_forms():
    """API endpoint to list all forms"""
    try:
        from utils.form_generator import FormGenerator
        form_generator = FormGenerator()
        forms = form_generator.list_all_forms()
        return jsonify(forms)
    except Exception as e:
        app.logger.error(f"Error listing forms: {str(e)}")
        return jsonify({"error": "Failed to list forms"}), 500

@app.route('/api/forms/<form_id>', methods=['DELETE'])
def delete_form(form_id):
    """API endpoint to delete a form"""
    try:
        from utils.form_generator import FormGenerator
        form_generator = FormGenerator()
        success = form_generator.delete_form(form_id)
        if success:
            return jsonify({"message": "Form deleted successfully"})
        else:
            return jsonify({"error": "Form not found"}), 404
    except Exception as e:
        app.logger.error(f"Error deleting form {form_id}: {str(e)}")
        return jsonify({"error": "Failed to delete form"}), 500

@app.route('/form/<form_id>')
def display_form(form_id):
    """Display generated form"""
    try:
        # Load form data from form generator
        from utils.form_generator import FormGenerator
        form_generator = FormGenerator()
        form_data = form_generator.get_form_data(form_id)

        if not form_data:
            return "Form not found", 404

        return render_template('form_template.html', form_data=form_data, form_id=form_id)
    except Exception as e:
        app.logger.error(f"Error displaying form {form_id}: {str(e)}")
        return "Form not found", 404

@app.route('/submit_form/<form_id>', methods=['POST'])
def submit_form(form_id):
    """Handle form submission"""
    try:
        # Get form data
        from utils.form_generator import FormGenerator
        form_generator = FormGenerator()
        stored_form_data = form_generator.get_form_data(form_id)

        if not stored_form_data:
            return "Form not found", 404

        # Process form submission
        submission_data = request.form.to_dict()
        app.logger.info(f"Form {form_id} submitted with data: {submission_data}")
        app.logger.info(f"Form type: {stored_form_data.get('type')}")
        app.logger.info(f"Header data: {stored_form_data.get('header_data')}")
        app.logger.info(f"Total questions in form: {len(stored_form_data.get('questions', []))}")

        # Start background processing for Monday.com updates
        import threading

        def process_monday_updates():
            """Background function to process Monday.com updates"""
            try:
                # Load configuration
                with open('setup/config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)

                form_type = stored_form_data.get('type')
                form_config = config.get(form_type, {})

                app.logger.info(f"Background processing - Form type: {form_type}, Config: {form_config}")

                if form_config.get('board_b'):
                    from utils.monday_api import MondayAPI
                    monday_api = MondayAPI()

                    # Get the item ID from webhook data
                    webhook_data = stored_form_data.get('webhook_data', {})
                    item_id = webhook_data.get('event', {}).get('pulseId')
                    board_b = form_config['board_b']

                    app.logger.info(f"Background processing - Saving responses to Board B: {board_b}, Item ID: {item_id}")

                    if item_id and board_b:
                        # Always create a new item in Board B for each form response
                        # Use Viagem from header data if available, otherwise use webhook pulse name
                        header_data = stored_form_data.get('header_data', {})
                        item_name = header_data.get('Viagem') or webhook_data.get('event', {}).get('pulseName', 'Resposta do Formulário')
                        app.logger.info(f"Background processing - Creating new item in Board B: {item_name}")

                        create_result = monday_api.create_item(board_b, item_name)
                        if create_result and create_result.get('create_item', {}).get('id'):
                            new_item_id = create_result['create_item']['id']
                            app.logger.info(f"Background processing - Created new item with ID: {new_item_id}")

                            # Prepare all updates in a batch
                            updates_to_process = []

                            # Add header data to destination board
                            header_data = stored_form_data.get('header_data', {})
                            
                            # Add Viagem as item name (already handled during item creation)
                            # Add other header fields to specific columns
                            if header_data.get('Destino'):
                                updates_to_process.append({
                                    'column_id': 'text_mkrb17ct',
                                    'value': header_data['Destino'],
                                    'description': f"Destino from header data"
                                })
                            
                            if header_data.get('Data'):
                                updates_to_process.append({
                                    'column_id': 'text_mksq2j87',
                                    'value': header_data['Data'],
                                    'description': f"Data from header data"
                                })
                            
                            if header_data.get('Cliente'):
                                updates_to_process.append({
                                    'column_id': 'text_mkrjdnry',
                                    'value': header_data['Cliente'],
                                    'description': f"Cliente from header data"
                                })

                            # Debug submission data
                            app.logger.info(f"Form submission data keys: {list(submission_data.keys())}")
                            app.logger.info(f"Form submission data: {submission_data}")

                            # Collect all updates from questions
                            for question in stored_form_data.get('questions', []):
                                question_id = question.get('id')
                                destination_column = question.get('destination_column')
                                question_destination_column = question.get('question_destination_column')
                                question_type = question.get('type')
                                question_text = question.get('text', '')[:50] + "..." if len(question.get('text', '')) > 50 else question.get('text', '')

                                app.logger.info(f"Processing question {question_id}: type={question_type}")
                                app.logger.info(f"  Text: {question_text}")
                                app.logger.info(f"  Destination column: '{destination_column}'")
                                app.logger.info(f"  Question destination column: '{question_destination_column}'")

                                # Skip divider questions
                                if question_type == 'divider':
                                    app.logger.info(f"Skipping divider question {question_id}")
                                    continue

                                # Check if this question was answered in the form
                                if question_id in submission_data:
                                    response_value = submission_data[question_id]
                                    app.logger.info(f"Question {question_id} answered with: '{response_value}' (type: {type(response_value)})")
                                    
                                    # Only process if there's a response and destination column
                                    if response_value and str(response_value).strip() and destination_column and destination_column.strip():
                                        # Preserve Portuguese values - don't translate
                                        if response_value == "yes":
                                            response_value = "Sim"
                                        elif response_value == "no":
                                            response_value = "Não"

                                        updates_to_process.append({
                                            'column_id': destination_column,
                                            'value': response_value,
                                            'description': f"Question {question_id} ({question_type}) response: {question_text}"
                                        })
                                        app.logger.info(f"Added to updates: {question_id} -> {destination_column} = '{response_value}'")
                                    elif not destination_column or not destination_column.strip():
                                        app.logger.warning(f"⚠️  Question {question_id} has no destination column configured")
                                    elif not response_value or not str(response_value).strip():
                                        app.logger.warning(f"Question {question_id} has empty response value: '{response_value}'")
                                else:
                                    app.logger.warning(f"Question {question_id} was not found in form submission data")

                                # For Monday column questions, also save the column value (question text)
                                if question_type == 'monday_column' and question_destination_column and question_destination_column.strip():
                                    column_value = question.get('column_value', '')
                                    if column_value and column_value not in ['', 'Dados não encontrados', 'Erro ao carregar dados', 'Dados não disponíveis', 'Configuração incompleta']:
                                        updates_to_process.append({
                                            'column_id': question_destination_column,
                                            'value': column_value,
                                            'description': f"Monday column question {question_id} text"
                                        })

                            # Process all updates
                            app.logger.info(f"Background processing - Processing {len(updates_to_process)} column updates")
                            successful_updates = 0
                            failed_updates = 0
                            
                            for update in updates_to_process:
                                try:
                                    app.logger.info(f"Background processing - {update['description']}: column={update['column_id']}, value={update['value']}")
                                    
                                    # Skip empty values
                                    if not update['value'] or str(update['value']).strip() == '':
                                        app.logger.warning(f"Skipping empty value for column {update['column_id']}")
                                        continue
                                    
                                    monday_api.update_item_column(
                                        board_id=board_b,
                                        item_id=new_item_id,
                                        column_id=update['column_id'],
                                        value=update['value']
                                    )
                                    app.logger.info(f"Background processing - Successfully updated column {update['column_id']}")
                                    successful_updates += 1
                                except Exception as e:
                                    app.logger.error(f"Background processing - Failed to update column {update['column_id']}: {str(e)}")
                                    failed_updates += 1
                            
                            app.logger.info(f"Background processing - Completed: {successful_updates} successful, {failed_updates} failed updates")

                            app.logger.info(f"Background processing - Completed all updates for form {form_id}")
                        else:
                            app.logger.error("Background processing - Failed to create item in Board B")
                    else:
                        app.logger.error("Background processing - Missing item_id or board_b configuration")
                else:
                    app.logger.warning(f"Background processing - No board_b configured for form type: {form_type}")

            except Exception as e:
                app.logger.error(f"Background processing error: {str(e)}")

        # Start background thread for Monday.com updates
        thread = threading.Thread(target=process_monday_updates, daemon=True)
        thread.start()

        app.logger.info(f"Form {form_id} processed successfully, Monday.com updates running in background")

        # Immediately return success page
        return render_template('success.html')

    except Exception as e:
        app.logger.error(f"Error submitting form {form_id}: {str(e)}")
        return "Error submitting form", 500

@app.errorhandler(404)
def not_found(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return "Internal server error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)