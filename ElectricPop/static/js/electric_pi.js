$(document).ready(function () {
    var newPowerMeter = ('<form method="POST">\n' +
        '                        <table border="1">\n' +
        '                            <tr>\n' +
        '                                <th colspan="4">I</th>\n' +
        '                                <th colspan="8">U</th>\n' +
        '                                <th colspan="4">Cosfi</th>\n' +
        '                            </tr>\n' +
        '                            <tr>\n' +
        '                                <th>A</th>\n' +
        '                                <th>A1</th>\n' +
        '                                <th>A2</th>\n' +
        '                                <th>A3</th>\n' +
        '                                <th>VLL</th>\n' +
        '                                <th>VLN</th>\n' +
        '                                <th>V1</th>\n' +
        '                                <th>V2</th>\n' +
        '                                <th>V3</th>\n' +
        '                                <th>V12</th>\n' +
        '                                <th>V23</th>\n' +
        '                                <th>V31</th>\n' +
        '                                <th>PF</th>\n' +
        '                                <th>PF1</th>\n' +
        '                                <th>PF2</th>\n' +
        '                                <th>PF3</th>\n' +
        '                            </tr>\n' +
        '                            <tr>\n' +
        '                                <td><input type="text" name="A" placeholder="A" class="textbox register" value="3913"></td>\n' +
        '                                <td><input type="text" name="A1" placeholder="A1" class="textbox register" value="3929"></td>\n' +
        '                                <td><input type="text" name="A2" placeholder="A2" class="textbox register" value="3943"></td>\n' +
        '                                <td><input type="text" name="A3" placeholder="A3" class="textbox register" value="3957"></td>\n' +
        '                                <td><input type="text" name="VLL" placeholder="VLL" class="textbox register" value="3909"></td>\n' +
        '                                <td><input type="text" name="VLN" placeholder="VLN" class="textbox register" value="3911"></td>\n' +
        '                                <td><input type="text" name="V1" placeholder="V1" class="textbox register" value="3927"></td>\n' +
        '                                <td><input type="text" name="V2" placeholder="V2" class="textbox register" value="3941"></td>\n' +
        '                                <td><input type="text" name="V3" placeholder="V3" class="textbox register" value="3955"></td>\n' +
        '                                <td><input type="text" name="V12" placeholder="V12" class="textbox register" value="3925"></td>\n' +
        '                                <td><input type="text" name="V23" placeholder="V23" class="textbox register" value="3939"></td>\n' +
        '                                <td><input type="text" name="V31" placeholder="V31" class="textbox register" value="3953"></td>\n' +
        '                                <td><input type="text" name="PF" placeholder="PF" class="textbox register" value="3907"></td>\n' +
        '                                <td><input type="text" name="PF1" placeholder="PF1" class="textbox register" value="3923"></td>\n' +
        '                                <td><input type="text" name="PF2" placeholder="PF2" class="textbox register" value="3937"></td>\n' +
        '                                <td><input type="text" name="PF3" placeholder="PF3" class="textbox register" value="3951"></td>\n' +
        '                            </tr>\n' +
        '                            <tr>\n' +
        '                                <td colspan="16"><input type="text" name="IDSLAVE" placeholder="ID-Slave" class="textbox" value="1"></td>\n' +
        '                            </tr>\n' +
        '                        </table>\n' +
        '                        <input type="button" class="button pmbutton" name="delete" value="Delete">\n' +
        '                        <input type="button" class="button pmbutton" name="save" value="Save">\n' +
        '                </form>');

    let temp = parseInt($('#temperature').text());
    let net = $('#network').text();

    if (temp <= 40) {
        $('#temperature').css('color', 'green');
    } else if (temp > 40 && temp <= 60) {
        $('#temperature').css('color', 'yellow');
    } else {
        $('#temperature').css('color', 'red');
    }

    if (temp == 'True') {
        $('#network').css('color', 'green');
    } else {
        $('#network').css('color', 'red');
    }

    $('body').on('click', '.addreg', function () {
        $('#wraptop').append(newPowerMeter);
    });

    $('body').on('click', '.pmbutton', function (event) {
        $.ajax({
            url: '/' + this.attributes['name'].value,
            data: $(this.parentNode).serialize(),
            type: 'POST',
        }).done(function (data) {
            if (JSON.parse(data).status) {
                alert('Lưu thành công !');
                if (JSON.parse(data).hasOwnProperty('delete')) {
                    location.reload();
                }
            } else {
                alert('Lưu thất bại !');
            }
        });
        event.preventDefault();
    })
});